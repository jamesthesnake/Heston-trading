"""Test that the project is set up correctly"""

def test_imports():
    """Test that main modules can be imported"""
    import src
    assert src is not None

def test_config_exists():
    """Test that configuration files exist"""
    from pathlib import Path
    assert Path("config/config.yaml").exists()
