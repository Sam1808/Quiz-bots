import argparse
import os


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--debug',
        type=bool,
        default=False,
        help='Turn DEBUG mode on'
    )
    return parser.parse_args()


def get_quiz_qa(folder_name):
    qa_files = os.listdir(folder_name)
    quiz_raw_data = []
    for qa_file in qa_files:
        qa_file_path = os.path.join(folder_name, qa_file)

        with open(qa_file_path, 'r', encoding='KOI8-R') as file:
            quiz_raw_data += file.read().split('\n\n')

    quiz_qa = {}
    for paragraph in quiz_raw_data:
        if 'Вопрос' in paragraph:
            index_after_colon = paragraph.find(':') + 1
            question = paragraph[index_after_colon:].strip()
        if 'Ответ' in paragraph:
            index_after_colon = paragraph.find(':') + 1
            answer = paragraph[index_after_colon:].strip()
            quiz_qa[question] = answer

    return quiz_qa
