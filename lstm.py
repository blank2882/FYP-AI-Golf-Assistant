import torch
import torch.nn as nn

class SwingLSTM(nn.Module):
    def __init__(self, input_dim=66, hidden_dim=128, output_dim=5):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        # x shape: (batch, time, features)
        out, _ = self.lstm(x)
        final = out[:, -1, :]
        return self.fc(final)
