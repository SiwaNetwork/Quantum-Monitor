#!/bin/bash
#
# PTP OCP Monitor Runner Script
# Запускает мониторинг PTP OCP устройства
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SRC_DIR="$SCRIPT_DIR/../src"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка прав root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Этот скрипт требует прав root для полного функционала"
        echo "Некоторые функции (ftrace, eBPF) не будут доступны"
        return 1
    fi
    return 0
}

# Проверка загрузки модуля ptp_ocp
check_module() {
    if ! lsmod | grep -q ptp_ocp; then
        warning "Модуль ptp_ocp не загружен"
        echo "Попытка загрузки модуля..."
        
        if check_root; then
            modprobe ptp_ocp
            if [ $? -eq 0 ]; then
                log "Модуль ptp_ocp успешно загружен"
            else
                error "Не удалось загрузить модуль ptp_ocp"
                return 1
            fi
        else
            error "Требуются права root для загрузки модуля"
            return 1
        fi
    else
        log "Модуль ptp_ocp загружен"
    fi
    return 0
}

# Поиск PTP OCP устройства
find_device() {
    local device=""
    
    # Проверяем PCI устройства
    for pci_dev in /sys/bus/pci/devices/*; do
        if [ -L "$pci_dev/driver" ]; then
            driver=$(basename $(readlink "$pci_dev/driver"))
            if [ "$driver" = "ptp_ocp" ]; then
                device="$pci_dev"
                log "Найдено PTP OCP устройство: $device"
                break
            fi
        fi
    done
    
    # Проверяем /sys/class/timecard
    if [ -z "$device" ] && [ -d "/sys/class/timecard" ]; then
        for tc_dev in /sys/class/timecard/*; do
            if [ -L "$tc_dev" ]; then
                device=$(readlink -f "$tc_dev")
                log "Найдено timecard устройство: $device"
                break
            fi
        done
    fi
    
    if [ -z "$device" ]; then
        error "PTP OCP устройство не найдено"
        return 1
    fi
    
    echo "$device"
    return 0
}

# Функция для показа информации об устройстве
show_device_info() {
    log "Получение информации об устройстве..."
    python3 "$SRC_DIR/sysfs_reader.py"
}

# Функция для запуска мониторинга
run_monitor() {
    local mode=$1
    local device=$2
    
    case "$mode" in
        "sysfs")
            log "Запуск мониторинга sysfs атрибутов..."
            python3 "$SRC_DIR/ptp_ocp_monitor.py" ${device:+-d "$device"}
            ;;
        "trace")
            if check_root; then
                log "Запуск трассировки функций..."
                python3 "$SRC_DIR/ptp_ocp_trace.py"
            else
                error "Требуются права root для трассировки функций"
                exit 1
            fi
            ;;
        "full")
            if check_root; then
                log "Запуск полного мониторинга..."
                python3 "$SRC_DIR/ptp_ocp_monitor.py" -v ${device:+-d "$device"}
            else
                warning "Запуск ограниченного мониторинга (без ftrace)"
                python3 "$SRC_DIR/ptp_ocp_monitor.py" ${device:+-d "$device"}
            fi
            ;;
        *)
            error "Неизвестный режим: $mode"
            exit 1
            ;;
    esac
}

# Главное меню
show_menu() {
    echo ""
    echo "=== PTP OCP Monitor ==="
    echo ""
    echo "1) Показать информацию об устройстве"
    echo "2) Мониторинг sysfs атрибутов"
    echo "3) Трассировка функций (требует root)"
    echo "4) Полный мониторинг"
    echo "5) Экспорт данных устройства в JSON"
    echo "6) Мониторинг конкретного атрибута"
    echo "q) Выход"
    echo ""
    echo -n "Выберите опцию: "
}

# Основная функция
main() {
    log "PTP OCP Monitor запущен"
    
    # Проверяем наличие Python
    if ! command -v python3 &> /dev/null; then
        error "Python3 не установлен"
        exit 1
    fi
    
    # Проверяем модуль
    if ! check_module; then
        warning "Продолжение без загруженного модуля может привести к ошибкам"
    fi
    
    # Находим устройство
    device=$(find_device)
    if [ $? -ne 0 ]; then
        warning "Устройство не найдено, некоторые функции могут быть недоступны"
        device=""
    fi
    
    # Интерактивный режим
    while true; do
        show_menu
        read -r choice
        
        case "$choice" in
            1)
                show_device_info
                ;;
            2)
                run_monitor "sysfs" "$device"
                ;;
            3)
                run_monitor "trace" "$device"
                ;;
            4)
                run_monitor "full" "$device"
                ;;
            5)
                log "Экспорт данных в JSON..."
                filename="ptp_ocp_export_$(date +%Y%m%d_%H%M%S).json"
                python3 "$SRC_DIR/sysfs_reader.py" -e "$filename"
                log "Данные экспортированы в $filename"
                ;;
            6)
                echo -n "Введите путь к устройству [$device]: "
                read -r custom_device
                custom_device=${custom_device:-$device}
                
                echo -n "Введите имя атрибута: "
                read -r attr
                
                echo -n "Интервал обновления (сек) [1]: "
                read -r interval
                interval=${interval:-1}
                
                python3 "$SRC_DIR/sysfs_reader.py" -m "$custom_device" "$attr" -i "$interval"
                ;;
            q|Q)
                log "Выход из программы"
                exit 0
                ;;
            *)
                error "Неверный выбор"
                ;;
        esac
        
        echo ""
        echo "Нажмите Enter для продолжения..."
        read -r
    done
}

# Обработка параметров командной строки
if [ $# -gt 0 ]; then
    case "$1" in
        --help|-h)
            echo "Использование: $0 [опции]"
            echo ""
            echo "Опции:"
            echo "  --sysfs     Запустить только мониторинг sysfs"
            echo "  --trace     Запустить только трассировку функций"
            echo "  --full      Запустить полный мониторинг"
            echo "  --info      Показать информацию об устройстве"
            echo "  --help      Показать эту справку"
            exit 0
            ;;
        --sysfs)
            check_module
            device=$(find_device)
            run_monitor "sysfs" "$device"
            exit 0
            ;;
        --trace)
            check_module
            run_monitor "trace" ""
            exit 0
            ;;
        --full)
            check_module
            device=$(find_device)
            run_monitor "full" "$device"
            exit 0
            ;;
        --info)
            check_module
            show_device_info
            exit 0
            ;;
        *)
            error "Неизвестная опция: $1"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
else
    # Интерактивный режим
    main
fi