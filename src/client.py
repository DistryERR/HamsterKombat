from http.client import HTTPSConnection, HTTPException
from src.devices import DEVICES
import logging
import json
import gzip
import zlib
import ssl
import socket

DECOMPRESSORS = {}
DECOMPRESSORS["gzip"] = gzip.decompress
DECOMPRESSORS["deflate"] = zlib.decompress

try:
    import brotli

    DECOMPRESSORS["br"] = brotli.decompress
except:
    pass


def GetHeaders(device):
    deviceHeaders = DEVICES[device]
    headers = {
        "Authorization": "Bearer {0}",
        "Accept": "{1}",
        "Content-Type": "{2}",
        "Origin": "https://hamsterkombat.io",
        "Referer": "https://hamsterkombat.io/",
        "Sec-Ch-Ua": deviceHeaders.get("Sec-Ch-Ua"),
        "Sec-Ch-Ua-Mobile": deviceHeaders.get("Sec-Ch-Ua-Mobile"),
        "Sec-Ch-Ua-Platform": deviceHeaders.get("Sec-Ch-Ua-Platform"),
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": deviceHeaders.get("User-Agent"),
        "Accept-Encoding": ", ".join(DECOMPRESSORS.keys()),
        "Accept-Language": "ru,en;q=0.9",
        "Content-Length": "{3}",
        "Connection": "keep-alive",
    }
    return {k: v for k, v in headers.items() if v}


class Client:
    API = "api.hamsterkombat.io"

    def __init__(self, authToken, device, proxy: str = None):
        if not authToken or not device:
            raise ValueError

        if proxy:
            self.__conn = HTTPSConnection(proxy, timeout=30)
            self.__conn.set_tunnel(self.API, 443)
        else:
            self.__conn = HTTPSConnection(self.API, 443, timeout=30)

        self.headers = GetHeaders(device)
        self.authToken = authToken
        self.proxy = proxy

    def __request(self, method, url, data=None):
        body = (json.dumps(data) if data else "").encode("utf-8")
        try:
            self.__conn.putrequest(method, url, False, True)
            args = (
                self.authToken,
                "application/json" if body else "*/*",
                "application/json" if body else "",
                len(body),
            )
            for k, v in self.headers.items():
                value = v.format(*args)
                if value:
                    self.__conn.putheader(k, value)
            self.__conn.endheaders(body)
        except:
            self.__conn.close()
            raise

    def __response(self):
        try:
            response = self.__conn.getresponse()
            responseData = response.read()

            encoding = response.headers.get("content-encoding", "identity")

            if encoding != "identity":
                decompressor = DECOMPRESSORS.get(encoding, None)
                if callable(decompressor):
                    responseData = decompressor(responseData)
                else:
                    raise HTTPException("Unsupported content encoding: %s" % (encoding))

            if self.proxy:
                self.__conn.close()

            return response, responseData
        except:
            self.__conn.close()
            raise

    def post(self, url, data=None):
        logging.debug("Sending request to %s", url)
        maxAttempts = 4
        attempt = 1
        while attempt <= maxAttempts:
            try:
                self.__request("POST", url, data)
                response, responseData = self.__response()

                self.lastResponseCode = response.status
                self.lastResponseData = responseData

                contentType = response.headers.get_content_type()

                if response.status != 200 or contentType != "application/json":
                    raise HTTPException(
                        "Bad response: %i (%s). Content: %s..."
                        % (response.status, response.reason, responseData[:128])
                    )

                return json.loads(responseData)
            except (
                TimeoutError,
                ConnectionResetError,
                ssl.SSLEOFError,
                socket.gaierror,
            ) as e:
                logging.debug(
                    "%s: %s. Attempt %i/%i", type(e).__name__, e, attempt, maxAttempts
                )
            attempt += 1
        raise ConnectionError("Remote host is not responding: %s", e)
