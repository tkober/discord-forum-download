import json
import sys
from getpass import getpass
from os import path, mkdir

from discord.api import ApiClient
import logging
import re
import requests
import shutil

root = logging.getLogger()
root.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

apiClient = ApiClient()

emoji_re = r'(<:)([a-z,_,0-9]+)(:)([0-9]+)(>)'


def assert_status_code(status_code: int, content: dict, expectation: int = 200):
    if status_code != expectation:
        raise RuntimeError(f'Error while request \nstatus_code: {status_code}\n\n{content}')


def download_top_messages(channelId: str):
    result, status_code = apiClient.channels().messages(channelId, around=channelId)
    assert_status_code(status_code, result)

    messages: list = result
    top_message_id = messages[0]['id'] if len(messages) > 0 else None
    messages.reverse()

    logging.info(f"+-- Loaded {len(messages)} messages around '{channelId}'")

    return messages, top_message_id


def download_messages_after(channelId: str, after_message_id: str):
    result, status_code = apiClient.channels().messages(channelId, after=after_message_id)
    assert_status_code(status_code, result)

    messages: list = result
    top_message_id = messages[0]['id'] if len(messages) > 0 else None
    messages.reverse()

    logging.info(f"+-- Loaded {len(messages)} messages after '{after_message_id}'")

    return messages, top_message_id


def download_channel_messages(channelId: str) -> list:
    all_messages = []

    last_messages, last_message_id = download_top_messages(channelId)

    while len(last_messages) > 0:
        all_messages.extend(last_messages)
        last_messages, last_message_id = download_messages_after(channelId, last_message_id)

    return all_messages


def download_channel_infos(channelId: str) -> dict:
    result, status_code = apiClient.channels().info(channelId)
    assert_status_code(status_code, result)

    return result


def download_profile(user_id: str, guild_id: str) -> dict:
    result, status_code = apiClient.users().profile(user_id, guild_id=guild_id, with_mutual_guilds=True)
    assert_status_code(status_code, result)

    return result


def collect_profile_names(user_ids: [str], guild_id: str) -> dict:
    result = {}
    for user_id in user_ids:
        profile = download_profile(user_id, guild_id)
        name = profile['user']['global_name']

        if 'guild_member' in profile:
            nick = profile['guild_member']['nick']
            name = nick if nick is not None else name

        logging.info(f"+-- Resolved user_id '{user_id}' to '{name}'")
        result[user_id] = name

    return result


def collect_attachments_from_messages(messages: [dict]) -> dict:
    result = {}
    for message in messages:

        if 'attachments' in message:
            for attachment in message['attachments']:
                result[attachment['id']] = {
                    'url': attachment['url'],
                    'content_type': attachment['content_type']
                }

    return result


def collect_emojis_from_messages(messages: [dict]) -> set:
    result = []

    for message in messages:

        if 'reactions' in message:
            for reaction in message['reactions']:
                if reaction['emoji']['id'] is not None:
                    result.append(reaction['emoji']['id'])

        result.extend(collect_emojis_from_message_content(message))

    return set(result)


def collect_emojis_from_message_content(message: dict) -> list:
    result = []
    content = message['content']
    matches = re.findall(emoji_re, content)
    for match in matches:
        result.append(match[3])

    return result


def collect_stickers_from_messages(messages: [dict]) -> set:
    result = []
    for message in messages:

        if 'sticker_items' in message:
            for sticker in message['sticker_items']:
                if sticker['id'] is not None:
                    result.append(sticker['id'])

    return set(result)


def download_file(url, file_name):
    res = requests.get(url, stream=True)

    if res.status_code == 200:
        with open(file_name, 'wb') as f:
            shutil.copyfileobj(res.raw, f)
    else:
        raise RuntimeError(f"Downloading '{url}' failed")


def download_stickers(sticker_ids, directory):
    mkdir(f'./{directory}/stickers')
    i = 1
    for sticker_id in sticker_ids:
        url = f'https://media.discordapp.net/stickers/{sticker_id}.webp'
        download_file(url, f'{directory}/stickers/{sticker_id}.webp')
        logging.info(f"+-- Downloaded sticker ({i}/{len(stickers)}) '{sticker_id}'")
        i += 1


def download_emoji(emoji_ids, directory):
    mkdir(f'./{directory}/emojis')
    i = 1
    for emoji_id in emoji_ids:
        url = f'https://cdn.discordapp.com/emojis/{emoji_id}.webp'
        download_file(url, f'{directory}/emojis/{emoji_id}.webp')
        logging.info(f"+-- Downloaded emoji ({i}/{len(emojis)}) '{emoji_id}'")
        i += 1


def download_attachments(attachments: dict, directory):
    mkdir(f'./{directory}/attachments')
    i = 1
    for key, attachment in attachments.items():
        file_extension = attachment['content_type'].split('/')[-1]
        url = attachment['url']
        download_file(url, f'{directory}/attachments/{key}.{file_extension}')
        logging.info(f"+-- Downloaded attachment ({i}/{len(attachments)}) '{url}'")
        i += 1


def save_information(channel_messages: [dict], profiles: dict, directory: str):
    with open(f'{directory}/messages.json', "w") as messages_file:
        json.dump(channel_messages, messages_file, indent='\t')

    with open(f'{directory}/profiles.json', "w") as profiles_file:
        json.dump(profiles, profiles_file, indent='\t')


if __name__ == '__main__':

    logging.info('\nPlease log into Discord')
    login = input('Discord login:')
    password = getpass('Password:')

    _, status_code = apiClient.login(login, password)
    if status_code != 200:
        logging.error('\nLogin failed. Please verify that your login and password are correct and try again.')
        exit(-1)

    logging.info('\nLogin successful')

    output_directory = './output/'
    if not path.exists(output_directory):
        mkdir(output_directory)

    logging.info('\nPlease provide the link to the channel')
    channel_link = ''
    while len(channel_link) == 0:
        channel_link = input('Channel link:')

    logging.info('\nPlease provide a name for your output directory')
    channel_id = channel_link.split('/')[-1]
    directory = input(f'Output directory: [{channel_id}]:') or channel_id

    while path.exists(f'{output_directory}{directory}'):
        directory = (input(
            f"Directory '{output_directory}{directory}' already exists. Please provide another name [{directory}]:")
                     or directory)

    directory = f'{output_directory}{directory}'
    mkdir(directory)

    logging.info('\nDownloading Channel Information')
    channel_info = download_channel_infos(channel_id)
    guild_id = channel_info['guild_id']
    channel_name = channel_info['name']
    member_count = channel_info['member_count']
    message_count = channel_info['message_count']
    logging.info(f"+-- Name: '{channel_name}'")
    logging.info(f'+-- Members: {member_count}')
    logging.info(f'+-- Messages: {message_count}')

    logging.info('\nDownloading Channel Messages')
    channel_messages = download_channel_messages(channel_id)

    logging.info('\nDownloading User Profiles')
    user_ids = set([message['author']['id'] for message in channel_messages])
    profiles = collect_profile_names(user_ids, guild_id)

    save_information(channel_messages, profiles, directory)

    logging.info('\nDownloading Emojis')
    emojis = collect_emojis_from_messages(channel_messages)
    logging.info(f'+-- Collected {len(emojis)} emojis')
    download_emoji(emojis, directory)

    logging.info('\nDownloading Stickers')
    stickers = collect_stickers_from_messages(channel_messages)
    logging.info(f'+-- Collected {len(stickers)} stickers')
    download_stickers(list(stickers), directory)

    logging.info('\nDownloading Attachments')
    attachments = collect_attachments_from_messages(channel_messages)
    logging.info(f'+-- Collected {len(attachments)} attachments')
    download_attachments(attachments, directory)

    logging.info('\nExport completed')
    logging.info(f'Your data can be found here: {path.abspath(directory)}')
