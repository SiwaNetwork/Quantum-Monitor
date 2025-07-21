"""
FastAPI веб-сервер для QUANTUM-PCI Configuration Tool
Предоставляет REST API и WebSocket для управления устройством
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ..core.device import QuantumPCIDevice
from ..core.exceptions import QuantumPCIError, DeviceNotFoundError
from .status_reader import StatusReader


# Модели данных для API
class DeviceInfo(BaseModel):
    device_path: str
    serial_number: str
    current_clock_source: str
    gnss_sync: bool
    timestamp: str


class ClockSourceRequest(BaseModel):
    source: str = Field(..., description="Clock source (INTERNAL, GNSS, EXTERNAL, etc.)")


class SMAPortRequest(BaseModel):
    port: int = Field(..., ge=1, le=4, description="SMA port number (1-4)")
    signal: str = Field(..., description="Signal type")


class SMAConfiguration(BaseModel):
    inputs: Dict[str, str]
    outputs: Dict[str, str]


class HealthStatus(BaseModel):
    healthy: bool
    checks: Dict[str, bool]
    timestamp: str


class FullStatus(BaseModel):
    device_info: DeviceInfo
    health_status: HealthStatus
    sma_config: SMAConfiguration


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                await self.disconnect_safely(connection)

    async def disconnect_safely(self, websocket: WebSocket):
        try:
            await websocket.close()
        except:
            pass
        finally:
            self.disconnect(websocket)


class QuantumPCIWebAPI:
    """Веб API для QUANTUM-PCI устройства"""
    
    def __init__(self, device_path: Optional[str] = None, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        # FastAPI приложение
        self.app = FastAPI(
            title="QUANTUM-PCI Web Interface",
            description="Веб интерфейс для управления QUANTUM-PCI устройством",
            version="2.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # WebSocket manager
        self.manager = ConnectionManager()
        
        # Устройство и статус-ридер
        try:
            self.device = QuantumPCIDevice(device_path)
            self.status_reader = StatusReader(self.device)
        except Exception as e:
            self.logger.error(f"Failed to initialize device: {e}")
            self.device = None
            self.status_reader = None
        
        # Настройка статических файлов и шаблонов
        self._setup_static_files()
        
        # Настройка маршрутов
        self._setup_routes()
        
        # Мониторинг задача
        self.monitoring_task = None
    
    def _setup_static_files(self):
        """Настройка статических файлов и шаблонов"""
        # Создаем директории если их нет
        static_dir = Path(__file__).parent.parent.parent / "web" / "static"
        templates_dir = Path(__file__).parent.parent.parent / "web" / "templates"
        
        static_dir.mkdir(parents=True, exist_ok=True)
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Подключаем статические файлы и шаблоны
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        self.templates = Jinja2Templates(directory=str(templates_dir))
    
    def _setup_routes(self):
        """Настройка маршрутов API"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            """Главная страница веб интерфейса"""
            return self.templates.TemplateResponse("index.html", {"request": request})
        
        @self.app.get("/api/health")
        async def health_check():
            """Проверка работоспособности API"""
            return {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "device_available": self.device is not None
            }
        
        @self.app.get("/api/device/info", response_model=DeviceInfo)
        async def get_device_info():
            """Получение информации об устройстве"""
            if not self.device:
                raise HTTPException(status_code=503, detail="Device not available")
            
            try:
                info = self.device.get_device_info()
                return DeviceInfo(
                    device_path=str(info['device_path']),
                    serial_number=info['serial_number'],
                    current_clock_source=info['current_clock_source'],
                    gnss_sync=info['gnss_sync'],
                    timestamp=datetime.now().isoformat()
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/device/status", response_model=FullStatus)
        async def get_full_status():
            """Получение полного статуса устройства"""
            if not self.status_reader:
                raise HTTPException(status_code=503, detail="Status reader not available")
            
            try:
                status = self.status_reader.get_full_status()
                
                device_info = DeviceInfo(
                    device_path=str(status['device_info']['device_path']),
                    serial_number=status['device_info']['serial_number'],
                    current_clock_source=status['device_info']['current_clock_source'],
                    gnss_sync=status['device_info']['gnss_sync'],
                    timestamp=datetime.now().isoformat()
                )
                
                health_status = HealthStatus(
                    healthy=status['health_status']['healthy'],
                    checks=status['health_status']['checks'],
                    timestamp=datetime.now().isoformat()
                )
                
                sma_config = SMAConfiguration(
                    inputs=status['sma_config']['inputs'],
                    outputs=status['sma_config']['outputs']
                )
                
                return FullStatus(
                    device_info=device_info,
                    health_status=health_status,
                    sma_config=sma_config
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/device/clock-source")
        async def set_clock_source(request: ClockSourceRequest):
            """Установка источника синхронизации"""
            if not self.device:
                raise HTTPException(status_code=503, detail="Device not available")
            
            try:
                success = self.device.set_clock_source(request.source)
                if success:
                    # Отправляем обновление через WebSocket
                    await self.manager.broadcast(json.dumps({
                        "type": "clock_source_changed",
                        "source": request.source,
                        "timestamp": datetime.now().isoformat()
                    }))
                    return {"success": True, "message": f"Clock source set to {request.source}"}
                else:
                    raise HTTPException(status_code=400, detail="Failed to set clock source")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/device/sma-input")
        async def set_sma_input(request: SMAPortRequest):
            """Настройка SMA входа"""
            if not self.device:
                raise HTTPException(status_code=503, detail="Device not available")
            
            try:
                success = self.device.set_sma_input(request.port, request.signal)
                if success:
                    # Отправляем обновление через WebSocket
                    await self.manager.broadcast(json.dumps({
                        "type": "sma_input_changed",
                        "port": request.port,
                        "signal": request.signal,
                        "timestamp": datetime.now().isoformat()
                    }))
                    return {"success": True, "message": f"SMA{request.port} input set to {request.signal}"}
                else:
                    raise HTTPException(status_code=400, detail="Failed to set SMA input")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/device/sma-output")
        async def set_sma_output(request: SMAPortRequest):
            """Настройка SMA выхода"""
            if not self.device:
                raise HTTPException(status_code=503, detail="Device not available")
            
            try:
                success = self.device.set_sma_output(request.port, request.signal)
                if success:
                    # Отправляем обновление через WebSocket
                    await self.manager.broadcast(json.dumps({
                        "type": "sma_output_changed",
                        "port": request.port,
                        "signal": request.signal,
                        "timestamp": datetime.now().isoformat()
                    }))
                    return {"success": True, "message": f"SMA{request.port} output set to {request.signal}"}
                else:
                    raise HTTPException(status_code=400, detail="Failed to set SMA output")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/device/sma-config", response_model=SMAConfiguration)
        async def get_sma_configuration():
            """Получение конфигурации SMA портов"""
            if not self.device:
                raise HTTPException(status_code=503, detail="Device not available")
            
            try:
                config = self.device.get_sma_configuration()
                return SMAConfiguration(
                    inputs=config['inputs'],
                    outputs=config['outputs']
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket для real-time обновлений"""
            await self.manager.connect(websocket)
            try:
                while True:
                    # Отправляем периодические обновления статуса
                    if self.status_reader:
                        try:
                            status = self.status_reader.get_full_status()
                            await websocket.send_text(json.dumps({
                                "type": "status_update",
                                "data": {
                                    "health": status['health_status']['healthy'],
                                    "timestamp": datetime.now().isoformat()
                                }
                            }))
                        except Exception as e:
                            self.logger.error(f"Error sending status update: {e}")
                    
                    await asyncio.sleep(5)  # Обновления каждые 5 секунд
                    
            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                self.manager.disconnect(websocket)
    
    async def start_monitoring(self):
        """Запуск фонового мониторинга"""
        if self.status_reader:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Цикл мониторинга для отправки обновлений"""
        while True:
            try:
                if self.status_reader:
                    status = self.status_reader.get_full_status()
                    await self.manager.broadcast(json.dumps({
                        "type": "monitoring_update",
                        "data": status,
                        "timestamp": datetime.now().isoformat()
                    }))
                await asyncio.sleep(10)  # Мониторинг каждые 10 секунд
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)  # Пауза при ошибке
    
    def run(self, debug: bool = False):
        """Запуск веб-сервера"""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="debug" if debug else "info",
            reload=debug
        )
        server = uvicorn.Server(config)
        
        # Запускаем мониторинг
        asyncio.run(self._run_with_monitoring(server))
    
    async def _run_with_monitoring(self, server):
        """Запуск сервера с мониторингом"""
        await self.start_monitoring()
        await server.serve()


def create_app(device_path: Optional[str] = None) -> FastAPI:
    """Фабрика для создания FastAPI приложения"""
    web_api = QuantumPCIWebAPI(device_path)
    return web_api.app


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="QUANTUM-PCI Web Interface")
    parser.add_argument("--device", help="Device path")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    web_api = QuantumPCIWebAPI(args.device, args.host, args.port)
    web_api.run(args.debug)