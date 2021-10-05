import logging
import os
import random
import redis
import telegram

from dotenv import load_dotenv
from functools import partial

from bot_utils import get_arguments
from bot_utils import get_quiz_qa
from enum import Enum
from telegram.ext import ConversationHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

QUIZ = Enum('Quiz', 'Question Answer')


def start(update, _):
    custom_keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счёт']]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text(
        'Привет. Готов к викторине? Начнем!',
        reply_markup=reply_markup
    )
    return QUIZ.Question


def cancel(update, _):
    update.message.reply_text(
        'Пока-пока!',
        reply_markup=telegram.ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def handle_new_question_request(update, _, quiz_qa, redis_base):
    question = random.choice([*quiz_qa])
    redis_base.set(f"tg-{update.message.from_user['id']}", question)
    update.message.reply_text(f'Вопрос: {question}')
    return QUIZ.Answer


def handle_solution_attempt(update, _, quiz_qa, redis_base):
    quiz_question = redis_base.get(
        f"tg-{update.message.from_user['id']}"
    ).decode('utf-8')
    message = 'Неправильно… Попробуешь ещё раз?'
    if update.message.text.lower() in quiz_qa[quiz_question].lower():
        update.message.reply_text(
            '''Правильно! Поздравляю!
            Для следующего вопроса нажми «Новый вопрос»''')
        return QUIZ.Question
    update.message.reply_text(message)


def handle_give_up(update, context, quiz_qa, redis_base):
    quiz_question = redis_base.get(
        f"tg-{update.message.from_user['id']}"
    ).decode('utf-8')
    answer = f'Ответ: {quiz_qa[quiz_question]}'
    update.message.reply_text(answer)
    handle_new_question_request(update, context, quiz_qa, redis_base)


if __name__ == '__main__':
    arguments = get_arguments()
    level = logging.DEBUG if arguments.debug else logging.INFO
    logging.basicConfig(level=level)

    load_dotenv()
    telegram_token = os.environ['TELEGRAM-TOKEN']
    redis_host = os.environ['REDIS-BASE']
    redis_port = os.environ['REDIS-PORT']
    redis_password = os.environ['REDIS-PASSWORD']

    logging.debug('Open Redis connection')
    redis_base = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password
    )

    logging.debug(
        'Read questions and answers from files & make QA dictionary'
    )
    quiz_qa = get_quiz_qa('questions')
    logging.debug('Prepare telegram bot')
    updater = Updater(token=telegram_token)
    dispatcher = updater.dispatcher

    partial_handle_new_question_request = partial(
        handle_new_question_request,
        quiz_qa=quiz_qa,
        redis_base=redis_base,
    )

    partial_handle_solution_attempt = partial(
        handle_solution_attempt,
        quiz_qa=quiz_qa,
        redis_base=redis_base,
    )

    partial_handle_give_up = partial(
        handle_give_up,
        quiz_qa=quiz_qa,
        redis_base=redis_base,
    )

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            QUIZ.Question: [
                MessageHandler(
                    Filters.regex('^(Новый вопрос)$'),
                    partial_handle_new_question_request
                )
            ],

            QUIZ.Answer: [
                MessageHandler(
                    Filters.regex('^(Сдаться)$'),
                    partial_handle_give_up
                ),
                MessageHandler(
                    Filters.text & ~Filters.command,
                    partial_handle_solution_attempt
                ),
            ]

        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(conversation_handler)

    logging.debug('Run telegram bot')
    updater.start_polling()
    updater.idle()
