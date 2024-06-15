# HamsterKombat
Утилита для автоматизации действий в HamsterKombat

## [Конфигурация](default.json)
| Параметр | Описание |
| --- | --- |
| AUTH_TOKEN | Токен авторизации |
| AUTO_UPGRADE | Активна ли автоматическая покупка улучшений |
| AUTO_UPGRADE_INTERVAL | Временной интервал в секундах, через который будет происходить покупка улучшений |
| MAX_UPGRADE_PRICE | Максимальная стоимость для покупки одного улучшения |
| MIN_BALANCE | Неснижаемый остаток монет при покупке улучшений |
| SEND_TAPS | Активна ли отправка кликов |
| CLAIM_DAILY_CIPHER | Выполнять ли ежедневный шифр |
| CLAIM_DAILY_TASK | Выполнять ли ежедневное задание |
| DEVICE | Название устройства, параметры которого будут использоваться при коммуникации с сервером игры |
| HTTP_PROXY | Адрес используемого прокси-сервера |

Самый простой способ получить токен авторизации - зайти в игру через бразуер и найти токен используя DevTools: Application -> Local storage -> authToken.

Также рекомендуется добавить в [devices](src/devices.py) параметры своего устройства (User-Agent, Sec-Ch-Ua, ...) по аналогии с уже имеющимися устройствами.

## Требования
Для работы утилиты требуется лишь [Python 3.9](https://www.python.org/downloads/) или его более новая версия.

Установка дополнтельных библиотек не требуется. Однако, не лишним будет установить библиотеку brotli.

## Установка и запуск
Утилита расчитана на использование в Termux, но может быть запущена и в Windows/Linux
```shell
~ $ git clone https://github.com/DistryERR/HamsterKombat.git
~ $ cd HamsterKombat
~/HamsterKombat $ python main.py my-config.json # Предварительно нужно создать файл конфигурации
~/HamsterKombat $ python main.py -d my-config.json # Запуск с выводом DEBUG-сообщений
~/HamsterKombat $ python main.py -d my-config.json > my-session.log & # Запуск в фоне с перенаправлением вывода в файл
```
