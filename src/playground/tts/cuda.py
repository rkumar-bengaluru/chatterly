import torch
print(torch.__version__)
print(torch.cuda.is_available())        # Should print: True
print(torch.cuda.get_device_name(0))    # Should print: NVIDIA GeForce RTX 3060

from TTS.api import TTS
print(TTS._version)  # Should be >= 0.23 (as of mid-2025)