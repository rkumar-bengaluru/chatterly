import torch
print(torch.__version__)
print(torch.cuda.is_available())        # Should be True
print(torch.version.cuda)              # e.g., '12.1'
print(torch.cuda.get_device_name(0))   # e.g., 'NVIDIA RTX 4090'