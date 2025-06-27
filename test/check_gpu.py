import torch
import subprocess


def check_gpu():
    print("=== Диагностика GPU ===")

    # 1. Проверка PyTorch
    print("\n[PyTorch]")
    print(f"Доступен CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Устройство 0: {torch.cuda.get_device_name(0)}")
        print(f"Память: {torch.cuda.get_device_properties(0).total_memory / 1024 ** 3:.2f} GB")

    # 2. Проверка Ollama
    print("\n[Ollama]")
    try:
        result = subprocess.run(["ollama", "serve"], capture_output=True, text=True, timeout=5)
        print("Ollama status:", "running" if result.returncode == 0 else "error")
        print("Ollama output:", result.stdout[:200] + "...")
    except subprocess.TimeoutExpired:
        print("Ollama: сервер запущен")
    except Exception as e:
        print(f"Ollama error: {str(e)}")


    # 3. Проверка драйверов
    print("\n[Драйверы]")
    try:
        # Для NVIDIA
        nvidia = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if nvidia.returncode == 0:
            print("NVIDIA драйверы:\n", nvidia.stdout.split('\n')[0:5])

        # Для AMD
        amd = subprocess.run(["rocm-smi"], capture_output=True, text=True)
        if amd.returncode == 0:
            print("AMD драйверы:\n", amd.stdout.split('\n')[0:5])
    except:
        print("Не удалось проверить драйверы")


if __name__ == "__main__":
    check_gpu()