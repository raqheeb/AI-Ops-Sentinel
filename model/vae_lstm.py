import torch
import torch.nn as nn

class VAELSTM(nn.Module):
    def __init__(self, input_dim=5, hidden_dim=64, latent_dim=16, num_layers=2):
        super(VAELSTM, self).__init__()

        # Encoder
        self.encoder_lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        # Decoder
        self.fc_decode = nn.Linear(latent_dim, hidden_dim)
        self.decoder_lstm = nn.LSTM(hidden_dim, input_dim, num_layers, batch_first=True)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        # Encode
        _, (h, _) = self.encoder_lstm(x)
        h = h[-1]  # last layer hidden state
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        z = self.reparameterize(mu, logvar)

        # Decode
        z_expanded = self.fc_decode(z).unsqueeze(1).repeat(1, x.size(1), 1)
        out, _ = self.decoder_lstm(z_expanded)
        return out, mu, logvar