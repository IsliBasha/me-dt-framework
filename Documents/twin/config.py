import os

TICK_INTERVAL_S             = 2.0
STATE_HISTORY_WINDOW        = 72
ALERT_THRESHOLD             = 0.75
AUTO_CONTAIN_THRESHOLD      = 0.92
PROBING_INTERVAL_TICKS      = 10
ANTHROPIC_MODEL             = "claude-sonnet-4-20250514"
MAX_TOKENS_MODE_A           = 512
MAX_TOKENS_MODE_B           = 800
MAX_TOKENS_MODE_C           = 1000
SERVER_HOST                 = "0.0.0.0"
SERVER_PORT                 = 8000
CUSUM_K                     = 0.5
CUSUM_H                     = 5.0
ISOFOREST_CONTAMINATION     = 0.05
ISOFOREST_RETRAIN_INTERVAL  = 20
WATER_NETWORK_FILE          = "networks/Net3.inp"
RECON_DURATION_TICKS        = 20
REPLAY_DELAY_TICKS          = 5
ATTACK_DURATION_TICKS       = 8
CHLORINE_MAX                = 4.0
PUMP_PRESSURE_DELTA_THRESHOLD = 10.0   # meters — swing over check window triggers W1
PUMP_PRESSURE_CHECK_WINDOW    = 3      # ticks to look back for W1 transient
LOG_LEVEL                   = "INFO"

ANTHROPIC_API_KEY           = os.environ.get("ANTHROPIC_API_KEY", "")

NET3_URL = (
    "https://raw.githubusercontent.com/USEPA/WNTR/main/wntr/tests/networks/Net3.inp"
)

WATER_DISPLAY_NODES = ["10", "15", "20", "35", "40", "50", "115", "117"]
POWER_DISPLAY_BUSES = [0, 4, 8, 12, 18, 32]
TRAFFIC_NODE_COUNT  = 12
