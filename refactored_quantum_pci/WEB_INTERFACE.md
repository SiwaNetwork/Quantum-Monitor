# QUANTUM-PCI Web Interface v2.0

Современный веб интерфейс для управления и мониторинга устройств QUANTUM-PCI.

## Особенности

- 🌐 **Современный веб интерфейс** на Vue.js 3 с красивым дизайном
- 📱 **Адаптивный дизайн** - работает на всех устройствах
- ⚡ **Real-time обновления** через WebSocket
- 🔄 **REST API** для интеграции с внешними системами
- 📊 **Мониторинг в реальном времени** состояния устройства
- 🎛️ **Интуитивное управление** SMA портами и источниками синхронизации
- 📚 **Автоматическая документация API** (Swagger/OpenAPI)
- 🛡️ **Безопасность** и обработка ошибок

## Быстрый старт

### 1. Установка зависимостей

```bash
cd refactored_quantum_pci
pip install -r requirements.txt
```

### 2. Запуск веб интерфейса

```bash
# Простой запуск
python main.py --web

# Или с параметрами
python main.py --web --host 0.0.0.0 --port 8000

# Альтернативный способ
python web_server.py
```

### 3. Открытие веб интерфейса

Откройте браузер и перейдите по адресу:
- **Веб интерфейс**: http://localhost:8000/
- **API документация**: http://localhost:8000/docs
- **API Explorer**: http://localhost:8000/redoc

## Интерфейс

### Главная страница

Веб интерфейс состоит из нескольких разделов:

#### 📟 Информация об устройстве
- Путь к устройству
- Серийный номер
- Текущий источник синхронизации
- Статус GNSS синхронизации
- Время последнего обновления

#### 💓 Состояние системы
- Общий статус здоровья устройства
- Детальные проверки состояния
- Индикаторы проблем

#### ⏰ Настройка источника синхронизации
- Выбор источника: INTERNAL, GNSS, EXTERNAL, PPS
- Применение настроек в реальном времени

#### 🔌 Настройка SMA портов
- **Входы**: конфигурация входных сигналов (PPS1, PPS2, TS1, TS2)
- **Выходы**: конфигурация выходных сигналов (PHC, GNSS1PPS, GNSS2PPS, MAC)
- Отдельная настройка каждого порта

#### 📊 Мониторинг в реальном времени
- Журнал событий в реальном времени
- Автоматическое обновление статуса
- Контроль запуска/остановки мониторинга

## API Endpoints

Веб интерфейс предоставляет REST API для интеграции:

### Основные endpoints

```http
GET  /api/health                 # Проверка здоровья API
GET  /api/device/info           # Информация об устройстве
GET  /api/device/status         # Полный статус устройства
GET  /api/device/sma-config     # Конфигурация SMA портов
POST /api/device/clock-source   # Установка источника синхронизации
POST /api/device/sma-input      # Настройка SMA входа
POST /api/device/sma-output     # Настройка SMA выхода
```

### WebSocket endpoint

```
WS   /ws                        # Real-time обновления
```

### Примеры использования API

#### Получение информации об устройстве
```bash
curl http://localhost:8000/api/device/info
```

#### Установка источника синхронизации
```bash
curl -X POST http://localhost:8000/api/device/clock-source \
  -H "Content-Type: application/json" \
  -d '{"source": "GNSS"}'
```

#### Настройка SMA порта
```bash
curl -X POST http://localhost:8000/api/device/sma-input \
  -H "Content-Type: application/json" \
  -d '{"port": 1, "signal": "PPS1"}'
```

## Параметры запуска

### Основное приложение (`main.py`)

```bash
python main.py --web [OPTIONS]

Options:
  --device PATH        Путь к устройству QUANTUM-PCI
  --host HOST          Хост для привязки (по умолчанию: 0.0.0.0)
  --port PORT          Порт для привязки (по умолчанию: 8000)
  --log-level LEVEL    Уровень логирования (DEBUG, INFO, WARNING, ERROR)
```

### Веб-сервер (`web_server.py`)

```bash
python web_server.py [OPTIONS]

Options:
  --device PATH        Путь к устройству QUANTUM-PCI
  --host HOST          Хост для привязки (по умолчанию: 0.0.0.0)
  --port PORT          Порт для привязки (по умолчанию: 8000)
  --debug              Включить режим отладки с auto-reload
  --log-level LEVEL    Уровень логирования
```

## Технические детали

### Архитектура

- **Backend**: FastAPI + Uvicorn
- **Frontend**: Vue.js 3 + Vanilla CSS
- **Real-time**: WebSockets
- **Стили**: Современный Material Design
- **Адаптивность**: CSS Grid + Flexbox

### Структура файлов

```
refactored_quantum_pci/
├── src/api/
│   └── web_api.py              # FastAPI веб-сервер
├── web/
│   ├── templates/
│   │   └── index.html          # Главная HTML страница
│   └── static/
│       ├── css/
│       │   └── main.css        # Стили интерфейса
│       └── js/
│           └── main.js         # JavaScript логика
├── web_server.py               # Отдельный запуск веб-сервера
└── main.py                     # Основное приложение
```

### Безопасность

- CORS настройки для безопасной работы
- Валидация входных данных через Pydantic
- Обработка ошибок и исключений
- Graceful shutdown при остановке

### Производительность

- Асинхронная обработка запросов
- WebSocket для минимизации нагрузки
- Кэширование статических файлов
- Эффективное управление соединениями

## Решение проблем

### Веб интерфейс не запускается

1. Проверьте установку зависимостей:
   ```bash
   pip install fastapi uvicorn websockets jinja2 python-multipart
   ```

2. Проверьте доступность порта:
   ```bash
   netstat -tulpn | grep :8000
   ```

3. Запустите с отладкой:
   ```bash
   python web_server.py --debug --log-level DEBUG
   ```

### Устройство не найдено

Веб интерфейс будет работать в ограниченном режиме, если устройство QUANTUM-PCI недоступно. Проверьте:

1. Подключение устройства
2. Загрузку драйвера: `modprobe ptp_ocp`
3. Права доступа к `/sys/class/timecard/`

### Проблемы с WebSocket

1. Проверьте настройки файрвола
2. Убедитесь что используется современный браузер
3. Проверьте консоль браузера на ошибки JavaScript

## Разработка

### Структура кода

- **web_api.py**: Основная логика веб-сервера
- **index.html**: HTML разметка интерфейса
- **main.css**: Стили и анимации
- **main.js**: Vue.js приложение и логика

### Добавление новых функций

1. Добавьте API endpoint в `web_api.py`
2. Обновите HTML шаблон в `index.html`
3. Добавьте CSS стили в `main.css`
4. Реализуйте логику в `main.js`

### Отладка

Используйте режим отладки для автоматической перезагрузки:

```bash
python web_server.py --debug
```

## Лицензия

© 2024 QUANTUM-PCI Development Team