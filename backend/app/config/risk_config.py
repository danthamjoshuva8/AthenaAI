from dataclasses import dataclass


@dataclass
class RiskConfig:

    partial_exit_2r = 0.50

    partial_exit_3r = 0.50

    stop_loss_type = "support"

    use_buffer = False