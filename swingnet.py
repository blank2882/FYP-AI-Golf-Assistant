import torch
from torch import nn

class SwingNet(nn.Module):
    def __init__(self, num_classes=8):
        super(SwingNet, self).__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), 
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.lstm = nn.LSTM(16*112*112, 128, batch_first=True)
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        B, T, C, H, W = x.shape
        x = x.view(B*T, C, H, W)
        feat = self.cnn(x)
        feat = feat.view(B, T, -1)
        out, _ = self.lstm(feat)
        return self.fc(out)
