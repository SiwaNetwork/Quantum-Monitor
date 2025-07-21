#!/usr/bin/env python3
"""
Установка зависимостей для веб интерфейса QUANTUM-PCI
"""

import subprocess
import sys

def install_dependencies():
    """Установка зависимостей для веб интерфейса"""
    
    print("🚀 Установка зависимостей для веб интерфейса QUANTUM-PCI...")
    print("=" * 60)
    
    # Список веб зависимостей
    web_deps = [
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0", 
        "websockets>=12.0",
        "jinja2>=3.1.2",
        "python-multipart>=0.0.6"
    ]
    
    # Проверка и установка pip
    try:
        import pip
    except ImportError:
        print("❌ pip не найден. Установите pip сначала.")
        sys.exit(1)
    
    success_count = 0
    total_count = len(web_deps)
    
    for dep in web_deps:
        print(f"\n📦 Устанавливаю {dep}...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], capture_output=True, text=True, check=True)
            
            print(f"✅ {dep} установлен успешно")
            success_count += 1
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка установки {dep}:")
            print(f"   {e.stderr}")
            continue
    
    print("\n" + "=" * 60)
    print(f"📊 Результат: {success_count}/{total_count} зависимостей установлено")
    
    if success_count == total_count:
        print("🎉 Все зависимости установлены успешно!")
        print("\nТеперь вы можете запустить веб интерфейс:")
        print("   python main.py --web")
        print("   или")
        print("   python web_server.py")
        print("\nДокументация: WEB_INTERFACE.md")
    else:
        print("⚠️  Некоторые зависимости не установились.")
        print("Попробуйте установить их вручную:")
        print("   pip install fastapi uvicorn[standard] websockets jinja2 python-multipart")
        
    print("=" * 60)


if __name__ == "__main__":
    install_dependencies()