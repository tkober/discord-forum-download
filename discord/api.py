import requests
import json

API_V9_BASE_URL = 'https://discord.com/api/v9'
API_V9_MESSAGES_LIMIT = 100


class Endpoint:

    def __init__(self, token: str, baseUrl: str):
        self.token = token
        self.baseUrl = baseUrl


class AuthEndpoint(Endpoint):

    def __init__(self, token: str | None, baseUrl: str):
        super().__init__(token, baseUrl + '/auth')

    def login(self, login: str, password: str) -> (dict, int):
        url = f'{self.baseUrl}/login'
        headers = {
            'Content-type': 'application/json'
        }
        body = {
            'login': login,
            'password': password
        }
        response = requests.post(url=url, json=body, headers=headers)

        return json.loads(response.text), response.status_code


class UsersEndpoint(Endpoint):

    def __init__(self, token: str, baseUrl: str):
        super().__init__(token, baseUrl + '/users')

    def profile(
            self,
            userId: str,
            guild_id: str = None,
            with_mutual_guilds: bool = False,
            with_mutual_friends_count: bool = False
    ) -> (dict, int):
        url = f'{self.baseUrl}/{userId}/profile'
        headers = {
            'authorization': self.token
        }
        params = {
            'guild_id': guild_id,
            'with_mutual_guilds': with_mutual_guilds,
            'with_mutual_friends_count': with_mutual_friends_count
        }
        response = requests.get(url=url, headers=headers, params=params)

        return json.loads(response.text), response.status_code


class ChannelsEndpoint(Endpoint):

    def __init__(self, token: str, baseUrl: str):
        super().__init__(token, baseUrl + '/channels')

    def info(self, channelId: str) -> (dict, int):
        url = f'{self.baseUrl}/{channelId}'
        headers = {
            'authorization': self.token
        }
        response = requests.get(url=url, headers=headers)

        return json.loads(response.text), response.status_code

    def messages(
            self,
            channelId: str,
            limit: int = API_V9_MESSAGES_LIMIT,
            after: str = None,
            around: str = None
    ) -> (dict, int):
        url = f'{self.baseUrl}/{channelId}/messages?limit={limit}'
        headers = {
            'authorization': self.token
        }
        params = {
            'after': after,
            'around': around
        }
        response = requests.get(url=url, headers=headers, params=params)

        return json.loads(response.text), response.status_code


class ApiClient:

    def __init__(
            self,
            token: str = None,
            baseUrl: str = API_V9_BASE_URL
    ):
        self.__token = token
        self.__baseUrl = baseUrl
        self.__auth = AuthEndpoint(None, self.__baseUrl)
        self.__channels = None
        self.__users = None

    def login(
            self,
            login: str,
            password: str,
            setToken=True
    ) -> (dict, int):
        content, status_code = self.auth().login(login, password)

        if status_code == 200 and setToken:
            self.__token = content['token']

        return content, status_code

    def auth(self) -> AuthEndpoint:
        return self.__auth

    def channels(self) -> ChannelsEndpoint:
        if self.__channels is None:
            self.__channels = ChannelsEndpoint(self.__token, self.__baseUrl)

        return self.__channels

    def users(self) -> UsersEndpoint:
        if self.__users is None:
            self.__users = UsersEndpoint(self.__token, self.__baseUrl)

        return self.__users
