import logging
import os
import random
import redis
import vk_api as vk

from bot_utils import get_arguments
from bot_utils import get_quiz_qa
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id


def send_message(event, vk_api, message):
    vk_api.messages.send(
        user_id=event.user_id,
        message=message,
        random_id=random.randint(1, 1000)
    )


def send_keyboard(event, vk_api):
    keyboard = VkKeyboard()
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.PRIMARY)
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message='Начинаем викторину'
    )


def send_new_question(event, vk_api, quiz_qa, redis_base):
    question = random.choice([*quiz_qa])
    redis_base.set(event.user_id, question)
    send_message(event, vk_api, message=f'Вопрос: {question}')


def check_answer(event, vk_api, quiz_qa, redis_base):
    question_by_user_id = redis_base.get(event.user_id)
    if question_by_user_id:
        question_by_user_id = question_by_user_id.decode('utf-8')
        message = 'Неправильно… Попробуешь ещё раз?'
        if event.text.lower() in quiz_qa[question_by_user_id].lower():
            message = '''
            Правильно! Поздравляю!
            Для следующего вопроса нажми «Новый вопрос»'''
        send_message(event, vk_api, message)
    else:
        message = '''
        Приветствую! Отправь start для запуска викторины
        и нажми кнопку «Новый вопрос»'''
        send_message(event, vk_api, message)


def give_up(event, vk_api, quiz_qa, redis_base):
    question_by_user_id = redis_base.get(event.user_id)
    if question_by_user_id:
        question_by_user_id = question_by_user_id.decode('utf-8')
        answer = f'Ответ: {quiz_qa[question_by_user_id]}'
        send_message(event, vk_api, answer)
        send_new_question(event, vk_api, quiz_qa, redis_base)


if __name__ == "__main__":
    arguments = get_arguments()
    level = logging.DEBUG if arguments.debug else logging.INFO
    logging.basicConfig(level=level)

    load_dotenv()
    vk_token = os.environ['VK-TOKEN']
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

    logging.debug('Run VK.com bot')
    vk_session = vk.VkApi(token=vk_token)
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text == 'start':
                send_keyboard(event, vk_api)
            elif event.text == 'Новый вопрос':
                send_new_question(event, vk_api, quiz_qa, redis_base)
            elif event.text == 'Сдаться':
                give_up(event, vk_api, quiz_qa, redis_base)
            else:
                check_answer(event, vk_api, quiz_qa, redis_base)
