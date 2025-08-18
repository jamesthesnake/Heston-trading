#!/usr/bin/env python3
"""
Test Interactive Brokers connection
"""
import sys
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ib_connection():
    """Test IB Gateway connection"""
    
    print("\n" + "="*60)
    print("    INTERACTIVE BROKERS CONNECTION TEST")
    print("="*60)
    
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        import threading
        
        class TestClient(EWrapper, EClient):
            def __init__(self):
                EWrapper.__init__(self)
                EClient.__init__(self, self)
                self.connected = False
                
            def nextValidId(self, orderId):
                self.connected = True
                print(f"\n✓ Connected to IB Gateway!")
                print(f"  Next valid order ID: {orderId}")
                
            def error(self, reqId, errorCode, errorString):
                if errorCode == 2104:
                    print("✓ Market data farm connected")
                elif errorCode < 1000:
                    print(f"✗ Error {errorCode}: {errorString}")
        
        # Create client
        client = TestClient()
        
        # Try to connect
        print("\nConnecting to IB Gateway...")
        print("  Host: 127.0.0.1")
        print("  Port: 7497 (paper trading)")
        
        client.connect("127.0.0.1", 7497, 999)
        
        # Start thread
        thread = threading.Thread(target=client.run, daemon=True)
        thread.start()
        
        # Wait for connection
        time.sleep(3)
        
        if client.isConnected():
            print("\n✓ CONNECTION SUCCESSFUL")
            client.disconnect()
            return 0
        else:
            print("\n✗ CONNECTION FAILED")
            print("\nTroubleshooting:")
            print("1. Is IB Gateway or TWS running?")
            print("2. Is API enabled in IB Gateway settings?")
            print("3. Is port 7497 correct? (7496 for live)")
            print("4. Check firewall settings")
            return 1
            
    except ImportError:
        print("\n✗ IB API not installed")
        print("Install with: pip install ibapi")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_ib_connection())
