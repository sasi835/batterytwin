from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from api.services import BatteryService  # Load native libraries before AppTest's script timeout.

APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'

@pytest.fixture(scope='module')
def dashboard():
    app=AppTest.from_file(str(APP),default_timeout=120).run()
    assert not app.exception
    return app

def test_dashboard_uses_saved_prediction(dashboard):
    values={metric.label:metric.value for metric in dashboard.metric}
    assert values['Next-cycle SOH']=='81.5%'
    assert values['Measured health']=='81.5%'

@pytest.mark.parametrize('page',['Predictions','Charge Tracking','Life Planning','Analytics','Model Performance','About & Requirements'])
def test_each_view_renders(dashboard,page):
    dashboard.sidebar.radio[0].set_value(page).run()
    assert not dashboard.exception,[e.message for e in dashboard.exception]

def test_custom_measurement_changes_forecast(dashboard):
    dashboard.sidebar.radio[0].set_value('Predictions').run()
    dashboard.number_input[0].set_value(1.3)
    dashboard.button[0].click().run()
    assert not dashboard.exception
    values={metric.label:metric.value for metric in dashboard.metric}
    assert values['Next-cycle SOH']!='81.5%'
    assert values['Remaining cycles']=='0'

def test_charge_form_runs_gru_and_forest(dashboard):
    dashboard.sidebar.radio[0].set_value('Charge Tracking').run()
    dashboard.button[0].click().run()
    assert not dashboard.exception
    values={metric.label:metric.value for metric in dashboard.metric}
    assert 0<float(values['Forest charge proxy'].rstrip('%'))<100
    assert 0<float(values['GRU charge proxy'].rstrip('%'))<100
