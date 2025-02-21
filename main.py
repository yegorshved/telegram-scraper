from configparser import ConfigParser
from pyrogram import Client
from pyrogram.raw.functions.stories import GetAllStories
from pyrogram.types import Chat
from pyrogram.types import Dialog
import asyncio
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait
import os
import csv

config = ConfigParser()

# читаем конфиг где API и прочее
base_path = '/home/alex/Documents/telegainfo'
config.read('config.ini')
API_ID = config.get('pyrogram', 'api_id')
API_HASH = config.get('pyrogram', 'api_hash')
RABOTABOT = config.get('pyrogram', 'RABOTA_BY_BOT')
PHONE_NUMBER = config.get('info', 'phonenumber')


async def sign_in(client: Client, phone_number: str):
    """
    Вход в Telegram по номеру телефона.
    Обрабатывает как SMS-подтверждение, так и двухфакторную аутентификацию (пароль).
    """

    try:
        # Если уже вошли – пропускаем
        await client.get_me()
        print("Already signed in.")
        return
    except Exception:
        print("Signing in...")
    await client.connect()  # Подключаемся к серверам Telegram

    # Запрашиваем код подтверждения
    sent_code = await client.send_code(phone_number)

    # Запрашиваем у пользователя код из SMS
    code = input("Enter Telegram code: ")

    # Пробуем выполнить вход с полученным кодом
    try:
        await client.sign_in(
            phone_number=phone_number,
            phone_code=code,
            phone_code_hash=sent_code.phone_code_hash
        )
    except Exception:
        print("Invalid code! Please check and try again.")
        return

    # Если требуется облачный пароль (2FA) – обрабатываем его
    try:
        await client.get_me()  # Проверяем, успешно ли вошли
        print("Successfully signed in!")
    except Exception:
        cloud_password = input("🔐 Enter your Telegram cloud password: ")
        await client.check_password(cloud_password)
        print("Successfully signed in with cloud password!")


async def download_stories(client: Client, chat: Chat, dir_path: str):
    print('downloading stories')
    # Если это не личный чат – выходим
    if chat.type in [ ChatType.CHANNEL, ChatType.GROUP, ChatType.SUPERGROUP, ChatType.BOT ]:
        return

    stories_dir = os.path.join(dir_path, "stories")
    user_id = chat.id
    print(f'stories_dir: {stories_dir}')
    print(f'user_id: {user_id}')
    # Получаем информацию о пользователе
    user = await client.get_users(user_id)

    username = chat.username if chat.username else ''

    stories = client.get_pinned_stories(username or user_id)

    # Создаем папку для фото, если ее нет
    if not os.path.exists(stories_dir):
        os.mkdir(stories_dir)
        print(f"Created directory for stories: {stories_dir}")

    index = 1

    async for story in stories:
        file_path = os.path.join(stories_dir, f'story_{username}_{str(story.id)}.jpeg')
        print(f'trying to download: {file_path}')
        if os.path.exists(file_path):
            print(f'{file_path} already exists, skipping.')
            continue
        await client.download_media(story, file_name=file_path)
        print(f"Downloaded story {index} for user {username or user_id}")
        index += 1
    print(f'index: {index}')
    try:
        if index == 1:
            os.rmdir(stories_dir)
    except OSError as e:
        print(f'Can\'t delete directory {stories_dir}, error: {e.strerror}')


async def make_dir(chat: Chat) -> str:
    name = ''
    try:
        if chat.last_name and chat.first_name:
            name = f"{chat.first_name}_{chat.last_name}"
        elif chat.first_name:
            name = chat.first_name
        elif chat.username:
            name = chat.username
        else:
            name = str(chat.id)
    except Exception:
        pass
    name = name.strip()
    path = os.path.join(base_path, name)
    try:
        os.mkdir(path)
        print(f"Directory '{path}' created.")
    except FileExistsError:
        print(f"Directory '{path}' already exists.")
    except Exception as e:
        print(f'Exception: {e}\nCouldn\'t create {name} folder!')
        return ''
    return path


async def download_all_photos(client: Client, chat: Chat, dir: str):
    # Если это не личный чат – выходим
    if chat.type in [ ChatType.CHANNEL, ChatType.GROUP, ChatType.SUPERGROUP, ChatType.BOT ]:
        return

    photos_dir = os.path.join(dir, "photos")
    user_id = chat.id

    # Получаем информацию о пользователе
    user = await client.get_users(user_id)

    username = chat.username if chat.username else ''

    photos = client.get_chat_photos(username or user_id)

    # Создаем папку для фото, если ее нет
    if not os.path.exists(photos_dir):
        os.mkdir(photos_dir)
        print(f"Created directory for photos: {photos_dir}")

    index = 1
    # Итерируем по фотографиям чата (предполагается, что метод get_chat_photos существует)
    async for photo in photos:
        file_path = os.path.join(photos_dir, f'photo_{username}_{str(photo.file_id)}.jpeg')
        if os.path.exists(file_path):
            print(f'{file_path} already exists, skipping.')
            continue
        await client.download_media(photo.file_id, file_name=file_path)
        print(f"Downloaded photo {index} for user {username or user_id}")
        index += 1
    try:
        if index == 1:
            os.rmdir(photos_dir)
    except OSError as e:
        print(f'Can\'t delete directory {photos_dir}, error: {e.strerror}')


async def write_info(dir: str, info: dict, filename: str = 'info.csv'):
    if dir:
        filename = os.path.join(dir, filename)
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=info.keys())
        writer.writeheader()
        writer.writerow(info)
    print(f"Wrote info to {filename}")


async def process_dialog(client: Client, dialog: Dialog):
    # Обрабатываем только личные чаты
    if dialog.chat.type != ChatType.PRIVATE:
        return

    # Получаем объект чата с обработкой FloodWait
    try:
        print('Getting chat...')
        chat: Chat = await client.get_chat(dialog.chat.id)
    except FloodWait as e:
        print(f"FloodWait during get_chat({dialog.chat.id}). Waiting {e.value} seconds.")
        await asyncio.sleep(e.value)
        chat = await client.get_chat(dialog.chat.id)

    # Получаем данные пользователя с обработкой FloodWait
    try:
        print('Getting user data...')
        user = await client.get_users(dialog.chat.id)
    except FloodWait as e:
        print(f"FloodWait during get_users({dialog.chat.id}). Waiting {e.value} seconds.")
        await asyncio.sleep(e.value)
        user = await client.get_users(dialog.chat.id)

    # handle birthday:
    birthday = ''
    if chat.birthday:
        birthday = f'{chat.birthday.day}.{chat.birthday.month}.{chat.birthday.year}'

    info = {
        'id': user.id,
        'username': user.username or 'N/A',
        'first name': user.first_name or 'N/A',
        'last name': user.last_name or 'N/A',
        'phone number': user.phone_number or 'N/A',
        'birthday': birthday or 'N/A',
        'bio': chat.bio or 'N/A',
        'description': chat.description or 'N/A',
    }
    print(f'info about user: {user.full_name}')
    print(info)
    # sleep(5)
    # print(f'Info: {info}')

    print('Making directory...')
    dir_name = await make_dir(chat)
    print(f'Directory: {dir_name}')

    #	print('Downloading photos...')
    await download_all_photos(client, chat, dir_name)
    #	print('Downloading stories...')
    await download_stories(client, chat, dir_name)

    print('Writing CSV file...')
    # await write_info(dir_name, info)
    print(f"Processed dialog for user {user.username or user.id}")


async def get_dialogs(client: Client):
    # target_username = "iamgulovser"
    async for dialog in client.get_dialogs():
        chat = dialog.chat

        print(f'processing\nchat.username: {chat.username}\nchat.first_name: {chat.first_name}')

        # print(f'Dialog: {dialog}') # commented because the output is VERY BIG
        try:
            print('Processing dialog...')
            print(f'Dialog: {dialog.chat.full_name}')
            await process_dialog(client, dialog)
        except FloodWait as e:
            print(f"FloodWait in process_dialog: waiting {e.value} seconds.")
            await asyncio.sleep(e.value)


async def main():
    # Создаем и используем клиент в асинхронном контексте
    async with Client('rabotabyupdater', api_id=API_ID, api_hash=API_HASH) as client:
        print('Signing in...')
        await sign_in(client, PHONE_NUMBER)
        print('Signed in.')
        print('Getting dialogs...')
        await get_dialogs(client)


if __name__ == "__main__":
    asyncio.run(main())

