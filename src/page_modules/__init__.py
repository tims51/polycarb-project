"""页面模块包"""

from .dashboard import render_dashboard
from .experiment_management import render_experiment_management
from .data_recording import render_data_recording
from .data_management import render_data_management

__all__ = [
    'render_dashboard',
    'render_experiment_management', 
    'render_data_recording',
    'render_data_management'
]