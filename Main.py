import os
import pickle
import streamlit as st
from dotenv import load_dotenv

# Для сбора компонентов GigaChat и RAG:
from langchain.chat_models.gigachat import GigaChat
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

import warnings  # Модуль для управления предупреждениями

warnings.filterwarnings("ignore")


# Установка переменной окружения
def set_environ():
    load_dotenv()
    os.environ["GIGACHAT_CREDENTIALS"] = os.getenv("GIGACHAT_CREDENTIALS")
    return


def uploading_file(path: str):
    loader = TextLoader(path, encoding="utf-8", autodetect_encoding=True)  # cp1251
    doc_1 = loader.load()
    return doc_1


def splitting_doc(doc_1):
    # Определяем сплиттер:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    # Разбиваем документ:
    split_doc_1 = text_splitter.split_documents(doc_1)
    return split_doc_1


def create_vector_storage(split_doc_1):
    # Если у вас нет видеокарты, укажите 'device': 'cpu'
    hf_embeddings_model = HuggingFaceEmbeddings(
        model_name="cointegrated/LaBSE-en-ru",
        model_kwargs={"device": "cpu"}
    )

    # Создаем FAISS индекс (базу векторов) с полученными эмбеддингами
    db_1 = FAISS.from_documents(split_doc_1, hf_embeddings_model)
    return db_1


def create_qa_chain(my_db_1):
    # Инициализируем языковую модель GigaChat
    # verify_ssl_certs=False – без использования сертификатов Минцифры
    llm = GigaChat(verify_ssl_certs=False, temperature=0.01)

    qa_chain_1 = RetrievalQA.from_chain_type(llm, retriever=my_db_1.as_retriever())
    return qa_chain_1


def get_current_files_names(directory_1):
    files_names = ""
    for f in os.listdir(directory_1):
        files_names += "\n" + f
    return files_names + "\n\n"


def array_of_file_names_by_their_indexes(files_numbers_1, directory_1):
    files_numbers_1 = files_numbers_1.split(" ")

    # Если в полученном массиве не только числа:
    for num in files_numbers_1:
        if not num.isdigit():
            return "It is not a number"

    # Иначе вытаскиваем индексы, файлы которых у нас есть:
    files_names_array_1 = []
    for f in os.listdir(directory_1):
        file_index = f.split("_")[0]
        for num in files_numbers_1:
            if int(num) == int(file_index):
                files_names_array_1.append(f)
    return files_names_array_1


# Соберём компоненты RAG по порядку
def to_collect_RAG(files_names_array_1):
    count = 0
    for filename in files_names_array_1:
        if count == 0:
            count += 1
            with open(f"documents/{filename}", 'rb') as file:
                db = pickle.load(file)
        else:
            with open(f"documents/{filename}", 'rb') as file:
                piece_db = pickle.load(file)
                db.merge_from(piece_db)

    chain = create_qa_chain(db)
    return chain


# Получаем вопрос от пользователя
def load_question():
    uploaded_question = st.text_input(label="Напишите вопрос")
    if uploaded_question is not None:
        return uploaded_question
    else:
        return None


# Получаем ответ на вопрос
def get_answer(question_1: str, files_names_array_1):
    qa_chain = to_collect_RAG(files_names_array_1)
    return qa_chain(question_1)


if __name__ == '__main__':
    set_environ()
    directory = "documents/"

    if not os.path.exists(directory):
        os.mkdir(directory)

    # Подключаем Streamlit
    st.set_page_config("Welcome")
    st.sidebar.success("Выберите вкладку здесь")
    st.title("Ответы на вопросы по нормативным документам. Языковая модель GigaChat")
    st.write("**Инструкция по использованию:** \n"
             "1) Загрузите свои документы в соседней вкладке\n"
             "2) Выберите номера документов для формирования ответа\n"
             "3) Напишите вопрос")

    total_files = len([name for name in os.listdir(directory)])
    if total_files == 0:
        st.write("**Для начала работы загрузите хотя бы один файл в соседней вкладке**")
    else:
        st.write(f"**Доступные документы**:\n{get_current_files_names(directory)}\n*Оставьте поле ниже пустым и "
                 "при ответе будут использованы все файлы*")
        # Создаем поле для ввода номеров документов:
        files_numbers = st.text_input(label="Через пробел напишите цифры документов, которые хотите использовать "
                                            "при получении ответа, затем нажмите кнопку 'Использовать эти документы'")
        files_num_but = st.button("Использовать эти документы")

        # Фрмируем массив названий документов, которые будет использовать для получения ответа
        if files_num_but and files_numbers == "":
            st.write("Сначала введите цифры в поле выше")

        if files_num_but and files_numbers != "":
            files_names_array = array_of_file_names_by_their_indexes(files_numbers, directory)
            if files_names_array == "It is not a number":
                st.write("Некорректный ввод, вводите целые числа документов через один пробел")
            elif len(files_names_array) == 0:
                st.write("Не найдены файлы с данными индексами, будут использованы все документы")
                for files in os.listdir(directory):
                    files_names_array.append(files)
            # Если какие-то документы попали в массив, будем использовать их для ответа
            else:
                st.write("В ответе будут использоваться документы:")
                st.write(files_names_array)

        else:
            files_names_array = []
            # Все файлы директории будут использованы для получения ответа:
            for files in os.listdir(directory):
                files_names_array.append(files)

        st.write("\n\nВведите вопрос ниже")
        question = load_question()
        result = st.button("Получить ответ")
        if result and question == "":
            st.write("Напишите вопрос!")
        elif result:
            context = get_answer(question, files_names_array)
            st.write(f"**Ответ на ваш вопрос:** {context['result']}")


# Какие требования к обеспечению безопасности в ходе создания, эксплуатации и вывода из
# эксплуатации значимых объектов нужно выполнять?
