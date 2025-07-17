"""
Исключения для работы с QUANTUM-PCI устройствами
"""


class QuantumPCIError(Exception):
    """Базовое исключение для всех ошибок QUANTUM-PCI"""
    pass


class DeviceNotFoundError(QuantumPCIError):
    """Исключение при отсутствии устройства"""
    pass


class DeviceAccessError(QuantumPCIError):
    """Исключение при ошибке доступа к устройству"""
    pass


class ConfigurationError(QuantumPCIError):
    """Исключение при ошибке конфигурации"""
    pass


class ValidationError(QuantumPCIError):
    """Исключение при ошибке валидации данных"""
    pass