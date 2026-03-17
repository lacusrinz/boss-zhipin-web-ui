# Enterprise Monitoring Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an automated enterprise monitoring system that queries RiskBird API every 5 minutes for newly registered companies and displays them in a web interface with configurable token management.

**Architecture:**
- APScheduler integrated with Flask for background task scheduling
- New SQLite tables for token storage, monitoring configs, and results
- Modular design: `riskbird_monitor.py` for monitoring logic, extended `database.py` for data access
- Web UI at `/monitoring` for configuration and results viewing

**Tech Stack:**
- APScheduler 3.10.4 for job scheduling
- Cryptography 41.0.7 for token encryption
- Flask 3.0+ (existing)
- SQLite (existing)
- Jinja2 templates (existing)

---

## Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Add new dependencies**

```bash
# Append to requirements.txt
echo "" >> requirements.txt
echo "# Enterprise Monitoring" >> requirements.txt
echo "APScheduler==3.10.4" >> requirements.txt
echo "cryptography==41.0.7" >> requirements.txt
```

**Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: Packages installed successfully

**Step 3: Verify installation**

```bash
python -c "import apscheduler; import cryptography; print('Dependencies OK')"
```

Expected: "Dependencies OK"

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add APScheduler and cryptography dependencies for monitoring module"
```

---

## Task 2: Database Schema - Create New Tables

**Files:**
- Modify: `code/database.py`
- Create: `tests/test_database_monitoring.py`

**Step 1: Write failing test for new tables**

Create `tests/test_database_monitoring.py`:

```python
#!/usr/bin/env python3
"""Tests for monitoring database tables"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from database import BOSSDatabase
import tempfile
import os

def test_init_monitoring_tables():
    """Test that monitoring tables are created"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()

        # Initialize monitoring tables
        result = db.init_monitoring_tables()

        assert result == True, "Table initialization should succeed"

        # Verify tables exist
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='riskbird_config'")
        assert cursor.fetchone() is not None, "riskbird_config table should exist"

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitoring_configs'")
        assert cursor.fetchone() is not None, "monitoring_configs table should exist"

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitored_companies'")
        assert cursor.fetchone() is not None, "monitored_companies table should exist"

        db.close()

def test_riskbird_config_crud():
    """Test riskbird_config CRUD operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert config
        db.insert_riskbird_config("token", "test_token_value")
        db.insert_riskbird_config("app_uuid", "test_uuid_value")

        # Read config
        token = db.get_riskbird_config("token")
        assert token == "test_token_value", f"Expected 'test_token_value', got {token}"

        # Update config
        db.update_riskbird_config("token", "new_token_value")
        token = db.get_riskbird_config("token")
        assert token == "new_token_value", f"Expected 'new_token_value', got {token}"

        db.close()

def test_monitoring_config_crud():
    """Test monitoring_configs CRUD operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert config
        config_id = db.insert_monitoring_config(
            config_name="Test Config",
            region_codes='["110000", "310000"]',
            interval_minutes=5
        )

        assert config_id is not None, "Config ID should not be None"

        # Read config
        configs = db.get_all_monitoring_configs()
        assert len(configs) == 1, f"Expected 1 config, got {len(configs)}"
        assert configs[0]['config_name'] == "Test Config"

        db.close()

def test_monitored_company_insert():
    """Test monitored_companies insert"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert config first
        config_id = db.insert_monitoring_config(
            config_name="Test Config",
            region_codes='["110000"]',
            interval_minutes=5
        )

        # Insert company
        company_id = db.insert_monitored_company({
            'config_id': config_id,
            'company_name': 'Test Company',
            'credit_code': '91110000123456789X',
            'reg_date': '2026-03-17',
            'region_code': '110000',
            'region_name': '北京市'
        })

        assert company_id is not None, "Company ID should not be None"

        # Check for duplicate
        company_id2 = db.insert_monitored_company({
            'config_id': config_id,
            'company_name': 'Test Company',
            'credit_code': '91110000123456789X',  # Same credit code
            'reg_date': '2026-03-17',
            'region_code': '110000',
            'region_name': '北京市'
        })

        assert company_id2 is None, "Duplicate credit_code should be rejected"

        db.close()
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/rinzlacus/Downloads/Coding/boss-zhipin-web-ui
python -m pytest tests/test_database_monitoring.py -v
```

Expected: FAIL - Method 'init_monitoring_tables' not found

**Step 3: Implement database methods in database.py**

Add to `code/database.py` after the `BOSSDatabase` class:

```python
    def init_monitoring_tables(self):
        """
        Initialize monitoring-related tables
        """
        try:
            # Create riskbird_config table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS riskbird_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL UNIQUE,
                    config_value TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT DEFAULT 'system'
                )
            """)

            # Create monitoring_configs table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_name TEXT NOT NULL,
                    region_codes TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    interval_minutes INTEGER DEFAULT 5,
                    reg_cap TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create monitored_companies table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitored_companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id INTEGER,
                    company_name TEXT NOT NULL,
                    credit_code TEXT UNIQUE,
                    reg_date TEXT,
                    reg_cap TEXT,
                    region_code TEXT,
                    region_name TEXT,
                    legal_representative TEXT,
                    contact TEXT,
                    address TEXT,
                    business_scope TEXT,
                    monitoring_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'riskbird',
                    is_processed BOOLEAN DEFAULT 0,
                    notes TEXT,
                    FOREIGN KEY (config_id) REFERENCES monitoring_configs (id)
                )
            """)

            # Create indexes
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_company_name
                ON monitored_companies(company_name)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monitoring_time
                ON monitored_companies(monitoring_time)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_time
                ON monitored_companies(config_id, monitoring_time)
            """)

            self.cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_credit_code
                ON monitored_companies(credit_code)
            """)

            self.conn.commit()
            logging.info("Monitoring tables initialized successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to initialize monitoring tables: {e}")
            return False

    def insert_riskbird_config(self, config_key: str, config_value: str) -> bool:
        """
        Insert or update riskbird config

        Args:
            config_key: Configuration key
            config_value: Configuration value

        Returns:
            bool: Success status
        """
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO riskbird_config (config_key, config_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (config_key, config_value))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to insert riskbird config: {e}")
            return False

    def get_riskbird_config(self, config_key: str) -> Optional[str]:
        """
        Get riskbird config value

        Args:
            config_key: Configuration key

        Returns:
            str: Configuration value or None
        """
        try:
            self.cursor.execute("""
                SELECT config_value FROM riskbird_config
                WHERE config_key = ? AND is_active = 1
            """, (config_key,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"Failed to get riskbird config: {e}")
            return None

    def get_all_riskbird_configs(self) -> Dict[str, str]:
        """
        Get all active riskbird configs

        Returns:
            dict: All config key-value pairs
        """
        try:
            self.cursor.execute("""
                SELECT config_key, config_value FROM riskbird_config
                WHERE is_active = 1
            """)
            return {row[0]: row[1] for row in self.cursor.fetchall()}
        except Exception as e:
            logging.error(f"Failed to get all riskbird configs: {e}")
            return {}

    def update_riskbird_config(self, config_key: str, config_value: str) -> bool:
        """
        Update riskbird config

        Args:
            config_key: Configuration key
            config_value: New configuration value

        Returns:
            bool: Success status
        """
        try:
            self.cursor.execute("""
                UPDATE riskbird_config
                SET config_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE config_key = ?
            """, (config_value, config_key))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to update riskbird config: {e}")
            return False

    def insert_monitoring_config(self, config_name: str, region_codes: str,
                                 interval_minutes: int = 5, reg_cap: str = None) -> Optional[int]:
        """
        Insert monitoring config

        Args:
            config_name: Configuration name
            region_codes: Region codes JSON string
            interval_minutes: Monitoring interval in minutes
            reg_cap: Registered capital filter (optional)

        Returns:
            int: Config ID or None
        """
        try:
            self.cursor.execute("""
                INSERT INTO monitoring_configs
                (config_name, region_codes, interval_minutes, reg_cap)
                VALUES (?, ?, ?, ?)
            """, (config_name, region_codes, interval_minutes, reg_cap))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logging.error(f"Failed to insert monitoring config: {e}")
            return None

    def get_all_monitoring_configs(self) -> List[Dict]:
        """
        Get all monitoring configs

        Returns:
            list: List of config dicts
        """
        try:
            self.cursor.execute("""
                SELECT id, config_name, region_codes, is_active,
                       interval_minutes, reg_cap, created_at, updated_at
                FROM monitoring_configs
                ORDER BY id DESC
            """)
            rows = self.cursor.fetchall()
            columns = ['id', 'config_name', 'region_codes', 'is_active',
                      'interval_minutes', 'reg_cap', 'created_at', 'updated_at']
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Failed to get monitoring configs: {e}")
            return []

    def get_monitoring_config(self, config_id: int) -> Optional[Dict]:
        """
        Get specific monitoring config

        Args:
            config_id: Configuration ID

        Returns:
            dict: Config data or None
        """
        try:
            self.cursor.execute("""
                SELECT id, config_name, region_codes, is_active,
                       interval_minutes, reg_cap, created_at, updated_at
                FROM monitoring_configs
                WHERE id = ?
            """, (config_id,))
            row = self.cursor.fetchone()
            if row:
                columns = ['id', 'config_name', 'region_codes', 'is_active',
                          'interval_minutes', 'reg_cap', 'created_at', 'updated_at']
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logging.error(f"Failed to get monitoring config: {e}")
            return None

    def update_monitoring_config(self, config_id: int, **kwargs) -> bool:
        """
        Update monitoring config

        Args:
            config_id: Configuration ID
            **kwargs: Fields to update

        Returns:
            bool: Success status
        """
        try:
            if not kwargs:
                return False

            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [config_id]

            self.cursor.execute(f"""
                UPDATE monitoring_configs
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to update monitoring config: {e}")
            return False

    def delete_monitoring_config(self, config_id: int) -> bool:
        """
        Delete monitoring config

        Args:
            config_id: Configuration ID

        Returns:
            bool: Success status
        """
        try:
            self.cursor.execute("DELETE FROM monitoring_configs WHERE id = ?", (config_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to delete monitoring config: {e}")
            return False

    def insert_monitored_company(self, company_data: Dict) -> Optional[int]:
        """
        Insert monitored company with duplicate check

        Args:
            company_data: Company data dict

        Returns:
            int: Company ID or None (if duplicate)
        """
        try:
            self.cursor.execute("""
                INSERT INTO monitored_companies
                (config_id, company_name, credit_code, reg_date, reg_cap,
                 region_code, region_name, legal_representative, contact,
                 address, business_scope)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_data.get('config_id'),
                company_data.get('company_name'),
                company_data.get('credit_code'),
                company_data.get('reg_date'),
                company_data.get('reg_cap'),
                company_data.get('region_code'),
                company_data.get('region_name'),
                company_data.get('legal_representative'),
                company_data.get('contact'),
                company_data.get('address'),
                company_data.get('business_scope')
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Duplicate credit_code
            logging.debug(f"Duplicate company: {company_data.get('credit_code')}")
            return None
        except Exception as e:
            logging.error(f"Failed to insert monitored company: {e}")
            return None

    def get_monitored_companies(self, config_id: int = None, limit: int = 100,
                                offset: int = 0) -> List[Dict]:
        """
        Get monitored companies with pagination

        Args:
            config_id: Filter by config ID (optional)
            limit: Number of results
            offset: Pagination offset

        Returns:
            list: List of company dicts
        """
        try:
            query = """
                SELECT id, config_id, company_name, credit_code, reg_date,
                       reg_cap, region_code, region_name, monitoring_time,
                       is_processed, source
                FROM monitored_companies
                WHERE 1=1
            """
            params = []

            if config_id:
                query += " AND config_id = ?"
                params.append(config_id)

            query += " ORDER BY monitoring_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            columns = ['id', 'config_id', 'company_name', 'credit_code', 'reg_date',
                      'reg_cap', 'region_code', 'region_name', 'monitoring_time',
                      'is_processed', 'source']
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logging.error(f"Failed to get monitored companies: {e}")
            return []

    def get_monitoring_stats(self) -> Dict:
        """
        Get monitoring statistics

        Returns:
            dict: Statistics
        """
        try:
            stats = {}

            # Total companies monitored
            self.cursor.execute("SELECT COUNT(*) FROM monitored_companies")
            stats['total_companies'] = self.cursor.fetchone()[0]

            # Today's additions
            self.cursor.execute("""
                SELECT COUNT(*) FROM monitored_companies
                WHERE DATE(monitoring_time) = DATE('now')
            """)
            stats['today_added'] = self.cursor.fetchone()[0]

            # Active configs
            self.cursor.execute("""
                SELECT COUNT(*) FROM monitoring_configs WHERE is_active = 1
            """)
            stats['active_configs'] = self.cursor.fetchone()[0]

            # Unprocessed companies
            self.cursor.execute("""
                SELECT COUNT(*) FROM monitored_companies WHERE is_processed = 0
            """)
            stats['unprocessed'] = self.cursor.fetchone()[0]

            return stats
        except Exception as e:
            logging.error(f"Failed to get monitoring stats: {e}")
            return {}
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_database_monitoring.py -v
```

Expected: PASS (all 4 tests pass)

**Step 5: Commit**

```bash
git add code/database.py tests/test_database_monitoring.py
git commit -m "feat: add monitoring database tables and CRUD operations"
```

---

## Task 3: Token Encryption Service

**Files:**
- Create: `code/token_service.py`
- Create: `tests/test_token_service.py`

**Step 1: Write failing test**

Create `tests/test_token_service.py`:

```python
#!/usr/bin/env python3
"""Tests for token encryption service"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from token_service import TokenService
import tempfile
import os

def test_encrypt_decrypt_token():
    """Test token encryption and decryption"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        key_path = tmp.name

    try:
        service = TokenService(key_path)
        original_token = "test_token_12345"

        # Encrypt
        encrypted = service.encrypt(original_token)
        assert encrypted != original_token, "Encrypted token should differ from original"
        assert len(encrypted) > 0, "Encrypted token should not be empty"

        # Decrypt
        decrypted = service.decrypt(encrypted)
        assert decrypted == original_token, "Decrypted token should match original"

    finally:
        if os.path.exists(key_path):
            os.unlink(key_path)

def test_mask_token():
    """Test token masking for display"""
    service = TokenService()

    # Long token
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.very_long_token_here"
    masked = service.mask_token(token)
    assert "..." in masked, "Masked token should contain ..."
    assert len(masked) < len(token), "Masked token should be shorter"

    # Short token
    short_token = "abc"
    masked = service.mask_token(short_token)
    assert len(masked) <= len(short_token), "Masked short token should not be longer"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_token_service.py -v
```

Expected: FAIL - Module 'token_service' not found

**Step 3: Implement TokenService**

Create `code/token_service.py`:

```python
#!/usr/bin/env python3
"""
Token encryption service for secure storage
"""
import base64
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


class TokenService:
    """Service for encrypting and decrypting sensitive tokens"""

    def __init__(self, key_path: str = None):
        """
        Initialize token service

        Args:
            key_path: Path to encryption key file (optional, uses default if not provided)
        """
        if key_path is None:
            # Default to project root
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent.parent
            key_path = base_dir / "data" / "encryption_key"

        self.key_path = Path(key_path)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)

        self._key = self._get_or_create_key()
        self.cipher = Fernet(self._key)

    def _get_or_create_key(self) -> bytes:
        """
        Get existing key or create new one

        Returns:
            bytes: Encryption key
        """
        if self.key_path.exists():
            with open(self.key_path, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_path, 'wb') as f:
                f.write(key)
            # Set file permissions to read/write only
            os.chmod(self.key_path, 0o600)
            return key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext

        Args:
            plaintext: Text to encrypt

        Returns:
            str: Encrypted text (base64 encoded)
        """
        if not plaintext:
            return ""

        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext

        Args:
            ciphertext: Encrypted text (base64 encoded)

        Returns:
            str: Decrypted plaintext
        """
        if not ciphertext:
            return ""

        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def mask_token(self, token: str, show_start: int = 8, show_end: int = 4) -> str:
        """
        Mask token for display purposes

        Args:
            token: Original token
            show_start: Number of characters to show at start
            show_end: Number of characters to show at end

        Returns:
            str: Masked token
        """
        if not token:
            return ""

        if len(token) <= show_start + show_end:
            return token

        return f"{token[:show_start]}...{token[-show_end:]}"
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_token_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add code/token_service.py tests/test_token_service.py
git commit -m "feat: add token encryption service"
```

---

## Task 4: RiskBird Monitor Core Logic

**Files:**
- Create: `code/riskbird_monitor.py`
- Modify: `code/riskbird_search.py` (extract reusable functions)
- Create: `tests/test_riskbird_monitor.py`

**Step 1: Write failing test**

Create `tests/test_riskbird_monitor.py`:

```python
#!/usr/bin/env python3
"""Tests for RiskBird monitor"""
import sys
from pathlib import Path
import tempfile
import os
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from riskbird_monitor import RiskBirdMonitor
from database import BOSSDatabase

def test_build_search_params():
    """Test building search params from config"""
    monitor = RiskBirdMonitor()

    config = {
        'region_codes': ['110000', '310000', '440000'],
        'interval_minutes': 5,
        'reg_cap': '5000￥'
    }

    params = monitor.build_search_params_from_config(config)

    assert 'aoData' in params, "Params should contain aoData"
    assert params['queryType'] == 'senior', "Query type should be senior"
    assert params['queryLimitType'] == 2, "Query limit type should be 2"

def test_parse_company_response():
    """Test parsing RiskBird API response"""
    monitor = RiskBirdMonitor()

    # Mock response
    mock_response = {
        'data': [
            {
                'id': '123',
                'name': 'Test Company',
                'creditNo': '91110000123456789X',
                'esDate': '2026-03-17',
                'regCap': '5000万人民币',
                'regOrg': '北京市市场监督管理局',
                'frname': '张三',
                'contact': '13800138000',
                'dom': '北京市朝阳区'
            }
        ]
    }

    companies = monitor.parse_companies_from_response(mock_response)

    assert len(companies) == 1, "Should parse 1 company"
    assert companies[0]['company_name'] == 'Test Company'
    assert companies[0]['credit_code'] == '91110000123456789X'

def test_run_monitoring_task_integration():
    """Test full monitoring task flow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Create monitoring config
        config_id = db.insert_monitoring_config(
            config_name="Test Config",
            region_codes='["110000"]',
            interval_minutes=5
        )

        monitor = RiskBirdMonitor(db)

        # Mock API call
        with patch.object(monitor, 'call_riskbird_api') as mock_api:
            mock_api.return_value = {
                'data': [
                    {
                        'id': '1',
                        'name': 'New Company',
                        'creditNo': '91110000999999999X',
                        'esDate': '2026-03-17',
                        'regCap': '1000万人民币',
                        'regOrg': '北京市市场监督管理局',
                        'frname': '李四',
                        'contact': '13900139000',
                        'dom': '北京市海淀区'
                    }
                ]
            }

            result = monitor.run_monitoring_task(config_id)

            assert result['success'] == True
            assert result['companies_added'] == 1

            # Verify company was saved
            companies = db.get_monitored_companies(config_id=config_id)
            assert len(companies) == 1
            assert companies[0]['company_name'] == 'New Company'
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_riskbird_monitor.py -v
```

Expected: FAIL - Module 'riskbird_monitor' not found

**Step 3: Extract reusable functions from riskbird_search.py**

First, let's extract common API functions from `code/riskbird_search.py` to make them reusable.

Add to `code/riskbird_search.py` (before the main section):

```python
# ==================== Reusable API Functions ====================

def get_riskbird_request_data(token: str, app_uuid: str, search_params: dict) -> dict:
    """
    Build RiskBird API request data with provided token

    Args:
        token: JWT token
        app_uuid: App device UUID
        search_params: Search parameters from build_search_params

    Returns:
        dict: Complete request data
    """
    cookies = {
        "app-uuid": app_uuid,
        "app-device": "WEB",
        "token": token,
    }

    return {
        "headers": HEADERS,
        "cookies": cookies,
        "json": search_params
    }

def call_riskbird_search_api(token: str, app_uuid: str, search_params: dict) -> dict:
    """
    Call RiskBird search API with provided credentials

    Args:
        token: JWT token
        app_uuid: App device UUID
        search_params: Search parameters

    Returns:
        dict: API response
    """
    request_data = get_riskbird_request_data(token, app_uuid, search_params)

    try:
        response = requests.post(
            SEARCH_API_URL,
            headers=request_data["headers"],
            cookies=request_data["cookies"],
            json=request_data["json"],
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {'error': 'unauthorized', 'message': 'Token expired or invalid'}
        else:
            return {'error': 'api_error', 'status_code': response.status_code}

    except requests.exceptions.RequestException as e:
        return {'error': 'request_failed', 'message': str(e)}
```

**Step 4: Implement RiskBirdMonitor class**

Create `code/riskbird_monitor.py`:

```python
#!/usr/bin/env python3
"""
RiskBird monitoring service
Automatically queries RiskBird API for newly registered companies
"""
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from database import BOSSDatabase
from riskbird_search import build_search_params, call_riskbird_search_api


class RiskBirdMonitor:
    """RiskBird API monitoring service"""

    def __init__(self, db: BOSSDatabase = None):
        """
        Initialize monitor

        Args:
            db: Database connection (optional, creates new if not provided)
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

    def build_search_params_from_config(self, config: Dict) -> Dict:
        """
        Build RiskBird API search params from monitoring config

        Args:
            config: Monitoring config dict

        Returns:
            dict: API request parameters
        """
        region_codes = json.loads(config.get('region_codes', '[]'))
        region_codes_str = ','.join(region_codes) if region_codes else ''

        # Set date range to today only
        today = datetime.now().strftime('%Y-%m-%d')
        es_date = f'{today}￥{today}'

        reg_cap = config.get('reg_cap', '')

        return build_search_params(
            regionid=region_codes_str,
            regcap=reg_cap,
            esdate=es_date
        )

    def call_riskbird_api(self, token: str, app_uuid: str, search_params: dict) -> dict:
        """
        Call RiskBird search API

        Args:
            token: JWT token
            app_uuid: App UUID
            search_params: Search parameters

        Returns:
            dict: API response
        """
        return call_riskbird_search_api(token, app_uuid, search_params)

    def parse_companies_from_response(self, response: dict) -> List[Dict]:
        """
        Parse companies from RiskBird API response

        Args:
            response: API response dict

        Returns:
            list: Parsed company data
        """
        companies = []

        if 'error' in response:
            self.logger.error(f"API error: {response.get('message')}")
            return companies

        data = response.get('data', [])

        if not isinstance(data, list):
            # Some API responses might have different structure
            data = data.get('aaData', []) if isinstance(data, dict) else []

        for item in data:
            try:
                company = {
                    'company_name': item.get('name', ''),
                    'credit_code': item.get('creditNo', ''),
                    'reg_date': item.get('esDate', ''),
                    'reg_cap': item.get('regCap', ''),
                    'legal_representative': item.get('frname', ''),
                    'contact': item.get('contact', ''),
                    'address': item.get('dom', ''),
                    'region_code': self._extract_region_code(item),
                    'region_name': self._extract_region_name(item)
                }
                companies.append(company)
            except Exception as e:
                self.logger.warning(f"Failed to parse company: {e}")
                continue

        return companies

    def _extract_region_code(self, company_data: dict) -> str:
        """Extract region code from company data"""
        # Implementation depends on actual API response structure
        # This is a placeholder
        return company_data.get('regionCode', '')

    def _extract_region_name(self, company_data: dict) -> str:
        """Extract region name from company data"""
        # Implementation depends on actual API response structure
        return company_data.get('regionName', '')

    def run_monitoring_task(self, config_id: int) -> Dict:
        """
        Execute a single monitoring task

        Args:
            config_id: Monitoring configuration ID

        Returns:
            dict: Task result with stats
        """
        result = {
            'success': False,
            'companies_added': 0,
            'companies_skipped': 0,
            'error': None
        }

        try:
            # Get config
            config = self.db.get_monitoring_config(config_id)
            if not config:
                result['error'] = f'Config {config_id} not found'
                return result

            # Get API credentials
            token = self.db.get_riskbird_config('token')
            app_uuid = self.db.get_riskbird_config('app_uuid')

            if not token or not app_uuid:
                result['error'] = 'API credentials not configured'
                return result

            # Build search params
            search_params = self.build_search_params_from_config(config)

            # Call API
            api_response = self.call_riskbird_api(token, app_uuid, search_params)

            if 'error' in api_response:
                if api_response['error'] == 'unauthorized':
                    result['error'] = 'Token expired or invalid'
                else:
                    result['error'] = api_response.get('message', 'API call failed')
                return result

            # Parse companies
            companies = self.parse_companies_from_response(api_response)

            # Save to database
            added = 0
            skipped = 0

            for company in companies:
                company['config_id'] = config_id
                company_id = self.db.insert_monitored_company(company)

                if company_id:
                    added += 1
                else:
                    skipped += 1

            result['success'] = True
            result['companies_added'] = added
            result['companies_skipped'] = skipped

            self.logger.info(f"Monitoring task completed: {added} added, {skipped} skipped")

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Monitoring task failed: {e}")

        return result
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_riskbird_monitor.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add code/riskbird_monitor.py code/riskbird_search.py tests/test_riskbird_monitor.py
git commit -m "feat: implement RiskBird monitoring service"
```

---

## Task 5: APScheduler Integration

**Files:**
- Modify: `code/web_app.py`
- Create: `tests/test_scheduler_integration.py`

**Step 1: Write test for scheduler integration**

Create `tests/test_scheduler_integration.py`:

```python
#!/usr/bin/env python3
"""Tests for APScheduler integration"""
import sys
from pathlib import Path
import tempfile
import os
import time

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from web_app import app, get_db, scheduler
from database import BOSSDatabase

def test_scheduler_initialization():
    """Test that scheduler is initialized"""
    assert scheduler is not None, "Scheduler should be initialized"
    assert scheduler.running, "Scheduler should be running"

def test_monitoring_job_scheduling():
    """Test scheduling a monitoring job"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Create config
        config_id = db.insert_monitoring_config(
            config_name="Test Job",
            region_codes='["110000"]',
            interval_minutes=1  # 1 minute for testing
        )

        # Add token
        db.insert_riskbird_config("token", "test_token")
        db.insert_riskbird_config("app_uuid", "test_uuid")

        # This would be called by API
        # For now, just verify the mechanism exists
        assert hasattr(scheduler, 'add_job'), "Scheduler should support add_job"
```

**Step 2: Integrate APScheduler into web_app.py**

Add to `code/web_app.py` after imports:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging

# ==================== Scheduler Setup ====================

def setup_scheduler():
    """
    Setup APScheduler for background monitoring tasks
    """
    # Configure jobstore to persist jobs in database
    jobstores = {
        'default': SQLAlchemyJobStore(url=f'sqlite:///{DB_PATH}')
    }

    # Configure executors
    executors = {
        'default': ThreadPoolExecutor(max_workers=5)
    }

    # Configure job defaults
    job_defaults = {
        'coalesce': True,  # Combine missed jobs into one
        'max_instances': 1,  # Only one instance of each job
        'misfire_grace_time': 300  # Grace period for missed jobs
    }

    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='Asia/Shanghai'
    )

    return scheduler

# Initialize scheduler
scheduler = setup_scheduler()
```

Add scheduler startup to `main()` function:

```python
def main():
    """启动 Flask 开发服务器"""
    print("=" * 60)
    print("BOSS 直聘 Web 管理界面")
    print("=" * 60)
    print("\n启动服务器...")
    print(f"数据库路径: {DB_PATH}")
    print("\n访问地址: http://localhost:5001")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 60)

    # 确保数据库存在并初始化
    db = get_db()
    if db.conn:
        db.init_monitoring_tables()  # Initialize monitoring tables
        db.close()

    # Start scheduler
    scheduler.start()
    print("✅ 后台任务调度器已启动")

    # 启动 Flask 开发服务器
    try:
        app.run(debug=True, host='127.0.0.1', port=5001, use_reloader=False)
    finally:
        scheduler.shutdown()
```

**Step 3: Add monitoring job management functions**

Add to `code/web_app.py`:

```python
# ==================== Monitoring Job Management ====================

def add_monitoring_job(config_id: int, interval_minutes: int):
    """
    Add a monitoring job to the scheduler

    Args:
        config_id: Monitoring configuration ID
        interval_minutes: Interval in minutes
    """
    from riskbird_monitor import RiskBirdMonitor

    job_id = f'monitoring_{config_id}'

    def run_job():
        db = get_db()
        if db.conn:
            try:
                monitor = RiskBirdMonitor(db)
                result = monitor.run_monitoring_task(config_id)
                logging.info(f"Job {job_id} completed: {result}")
            finally:
                db.close()

    scheduler.add_job(
        func=run_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        name=f'Monitoring Config {config_id}',
        replace_existing=True
    )

    logging.info(f"Added monitoring job: {job_id} (interval: {interval_minutes} min)")

def remove_monitoring_job(config_id: int):
    """
    Remove a monitoring job from the scheduler

    Args:
        config_id: Monitoring configuration ID
    """
    job_id = f'monitoring_{config_id}'
    try:
        scheduler.remove_job(job_id)
        logging.info(f"Removed monitoring job: {job_id}")
        return True
    except Exception as e:
        logging.error(f"Failed to remove job {job_id}: {e}")
        return False

def pause_monitoring_job(config_id: int):
    """Pause a monitoring job"""
    job_id = f'monitoring_{config_id}'
    try:
        scheduler.pause_job(job_id)
        return True
    except Exception as e:
        logging.error(f"Failed to pause job {job_id}: {e}")
        return False

def resume_monitoring_job(config_id: int):
    """Resume a paused monitoring job"""
    job_id = f'monitoring_{config_id}'
    try:
        scheduler.resume_job(job_id)
        return True
    except Exception as e:
        logging.error(f"Failed to resume job {job_id}: {e}")
        return False

def run_monitoring_job_now(config_id: int):
    """Run a monitoring job immediately"""
    job_id = f'monitoring_{config_id}'
    try:
        scheduler.run_job(job_id)
        return True
    except Exception as e:
        logging.error(f"Failed to run job {job_id}: {e}")
        return False
```

**Step 4: Run test**

```bash
python -m pytest tests/test_scheduler_integration.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add code/web_app.py tests/test_scheduler_integration.py
git commit -m "feat: integrate APScheduler for background monitoring tasks"
```

---

## Task 6: Monitoring API Endpoints

**Files:**
- Modify: `code/web_app.py`

**Step 1: Add token management endpoints**

```python
@app.route('/api/monitoring/token', methods=['GET'])
def get_token_config():
    """Get RiskBird token configuration (masked)"""
    from token_service import TokenService

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    configs = db.get_all_riskbird_configs()
    db.close()

    # Mask token for display
    token_service = TokenService()
    masked_configs = {}
    for key, value in configs.items():
        if key == 'token':
            masked_configs[key] = token_service.mask_token(value)
        else:
            masked_configs[key] = value

    return jsonify({'success': True, 'configs': masked_configs})


@app.route('/api/monitoring/token', methods=['POST'])
def save_token_config():
    """Save RiskBird token configuration"""
    from token_service import TokenService

    data = request.json
    token = data.get('token', '').strip()
    app_uuid = data.get('app_uuid', '').strip()
    userinfo = data.get('userinfo', '').strip()

    if not token or not app_uuid:
        return jsonify({'success': False, 'error': 'Token和App UUID不能为空'})

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    # Encrypt and save token
    token_service = TokenService()

    if token:
        encrypted_token = token_service.encrypt(token)
        db.insert_riskbird_config('token', encrypted_token)

    if app_uuid:
        db.insert_riskbird_config('app_uuid', app_uuid)

    if userinfo:
        db.insert_riskbird_config('userinfo', userinfo)

    db.close()

    return jsonify({'success': True, 'message': '配置已保存'})


@app.route('/api/monitoring/token/test', methods=['POST'])
def test_token_connection():
    """Test RiskBird token connection"""
    from token_service import TokenService
    from riskbird_search import build_search_params, call_riskbird_search_api

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    encrypted_token = db.get_riskbird_config('token')
    app_uuid = db.get_riskbird_config('app_uuid')

    if not encrypted_token or not app_uuid:
        db.close()
        return jsonify({'success': False, 'error': '请先配置Token'})

    # Decrypt token
    token_service = TokenService()
    try:
        token = token_service.decrypt(encrypted_token)
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': f'Token解密失败: {str(e)}'})

    db.close()

    # Test API call with minimal params
    test_params = build_search_params(
        regionid='110000',
        esdate='2026-03-17￥2026-03-17'
    )

    response = call_riskbird_search_api(token, app_uuid, test_params)

    if 'error' in response:
        if response['error'] == 'unauthorized':
            return jsonify({'success': False, 'error': 'Token无效或已过期'})
        else:
            return jsonify({'success': False, 'error': f'API调用失败: {response.get("message")}')

    return jsonify({'success': True, 'message': '连接测试成功'})
```

**Step 2: Add monitoring config endpoints**

```python
@app.route('/api/monitoring/configs', methods=['GET'])
def get_monitoring_configs():
    """Get all monitoring configurations"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    configs = db.get_all_monitoring_configs()
    db.close()

    return jsonify({'success': True, 'configs': configs})


@app.route('/api/monitoring/configs', methods=['POST'])
def create_monitoring_config():
    """Create a new monitoring configuration"""
    data = request.json
    config_name = data.get('config_name', '').strip()
    region_codes = data.get('region_codes', [])
    interval_minutes = data.get('interval_minutes', 5)
    reg_cap = data.get('reg_cap', '').strip()

    if not config_name:
        return jsonify({'success': False, 'error': '配置名称不能为空'})

    if not region_codes:
        return jsonify({'success': False, 'error': '请至少选择一个地区'})

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    # Convert region list to JSON string
    import json
    region_codes_json = json.dumps(region_codes)

    config_id = db.insert_monitoring_config(
        config_name=config_name,
        region_codes=region_codes_json,
        interval_minutes=interval_minutes,
        reg_cap=reg_cap if reg_cap else None
    )

    if config_id:
        # Add job to scheduler
        add_monitoring_job(config_id, interval_minutes)

        db.close()
        return jsonify({'success': True, 'config_id': config_id})
    else:
        db.close()
        return jsonify({'success': False, 'error': '创建配置失败'})


@app.route('/api/monitoring/configs/<int:config_id>', methods=['PUT'])
def update_monitoring_config(config_id):
    """Update monitoring configuration"""
    data = request.json

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    # Build update dict
    updates = {}
    if 'config_name' in data:
        updates['config_name'] = data['config_name']
    if 'region_codes' in data:
        import json
        updates['region_codes'] = json.dumps(data['region_codes'])
    if 'interval_minutes' in data:
        updates['interval_minutes'] = data['interval_minutes']
    if 'reg_cap' in data:
        updates['reg_cap'] = data['reg_cap']

    success = db.update_monitoring_config(config_id, **updates)

    if success and 'interval_minutes' in updates:
        # Update job schedule
        remove_monitoring_job(config_id)
        add_monitoring_job(config_id, updates['interval_minutes'])

    db.close()

    if success:
        return jsonify({'success': True, 'message': '配置已更新'})
    else:
        return jsonify({'success': False, 'error': '更新配置失败'})


@app.route('/api/monitoring/configs/<int:config_id>', methods=['DELETE'])
def delete_monitoring_config(config_id):
    """Delete monitoring configuration"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    # Remove from scheduler
    remove_monitoring_job(config_id)

    # Delete from database
    success = db.delete_monitoring_config(config_id)
    db.close()

    if success:
        return jsonify({'success': True, 'message': '配置已删除'})
    else:
        return jsonify({'success': False, 'error': '删除配置失败'})
```

**Step 3: Add job control endpoints**

```python
@app.route('/api/monitoring/jobs', methods=['GET'])
def get_monitoring_jobs():
    """Get all monitoring jobs status"""
    jobs = scheduler.get_jobs()

    job_list = []
    for job in jobs:
        if job.id.startswith('monitoring_'):
            config_id = int(job.id.split('_')[1])
            job_list.append({
                'id': job.id,
                'config_id': config_id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'paused': not job.next_run_time
            })

    return jsonify({'success': True, 'jobs': job_list})


@app.route('/api/monitoring/jobs/<int:config_id>/toggle', methods=['POST'])
def toggle_monitoring_job(config_id):
    """Toggle monitoring job (pause/resume)"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    config = db.get_monitoring_config(config_id)
    db.close()

    if not config:
        return jsonify({'success': False, 'error': '配置不存在'})

    # Check if job is paused
    job_id = f'monitoring_{config_id}'
    job = scheduler.get_job(job_id)

    if job:
        # Job exists, toggle it
        if hasattr(job.trigger, 'trigger'):
            # Already paused
            if resume_monitoring_job(config_id):
                return jsonify({'success': True, 'paused': False})
        else:
            # Running, pause it
            if pause_monitoring_job(config_id):
                return jsonify({'success': True, 'paused': True})
    else:
        return jsonify({'success': False, 'error': '任务不存在'})

    return jsonify({'success': False, 'error': '操作失败'})


@app.route('/api/monitoring/jobs/<int:config_id>/run-now', methods=['POST'])
def run_monitoring_job_now_endpoint(config_id):
    """Run monitoring job immediately"""
    success = run_monitoring_job_now(config_id)

    if success:
        return jsonify({'success': True, 'message': '任务已启动'})
    else:
        return jsonify({'success': False, 'error': '启动任务失败'})
```

**Step 4: Add data query endpoints**

```python
@app.route('/api/monitoring/companies', methods=['GET'])
def get_monitored_companies():
    """Get monitored companies with pagination"""
    config_id = request.args.get('config_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    companies = db.get_monitored_companies(
        config_id=config_id,
        limit=limit,
        offset=offset
    )

    # Get total count
    if config_id:
        db.cursor.execute("SELECT COUNT(*) FROM monitored_companies WHERE config_id = ?", (config_id,))
    else:
        db.cursor.execute("SELECT COUNT(*) FROM monitored_companies")
    total = db.cursor.fetchone()[0]

    db.close()

    return jsonify({
        'success': True,
        'companies': companies,
        'total': total,
        'limit': limit,
        'offset': offset
    })


@app.route('/api/monitoring/stats', methods=['GET'])
def get_monitoring_stats():
    """Get monitoring statistics"""
    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    stats = db.get_monitoring_stats()
    db.close()

    return jsonify({'success': True, 'stats': stats})


@app.route('/monitoring')
def monitoring_page():
    """Monitoring management page"""
    return render_template('monitoring.html')
```

**Step 5: Commit**

```bash
git add code/web_app.py
git commit -m "feat: add monitoring API endpoints for token/config/job/data management"
```

---

## Task 7: Frontend - Monitoring Page

**Files:**
- Create: `code/templates/monitoring.html`
- Modify: `code/templates/base.html` (add navigation link)

**Step 1: Create monitoring.html template**

Create `code/templates/monitoring.html`:

```html
{% extends "base.html" %}

{% block title %}企业监测 - BOSS直聘管理{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-8">企业监测管理</h1>

    <!-- Token Configuration Card -->
    <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-xl font-semibold mb-4">RiskBird API 配置</h2>

        <form id="token-form" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Token</label>
                <input type="text" name="token" id="token-input"
                       class="w-full border rounded px-3 py-2"
                       placeholder="输入JWT Token">
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">App UUID</label>
                <input type="text" name="app_uuid" id="uuid-input"
                       class="w-full border rounded px-3 py-2"
                       placeholder="输入App UUID">
            </div>

            <div class="flex space-x-4">
                <button type="submit"
                        class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                    保存配置
                </button>
                <button type="button" id="test-connection-btn"
                        class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                    测试连接
                </button>
            </div>
        </form>

        <div id="token-status" class="mt-4 hidden">
            <span class="text-sm">状态: <span id="status-text"></span></span>
        </div>
    </div>

    <!-- Monitoring Configuration Card -->
    <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-xl font-semibold mb-4">创建监测配置</h2>

        <form id="monitoring-config-form" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">配置名称</label>
                <input type="text" name="config_name" required
                       class="w-full border rounded px-3 py-2"
                       placeholder="如：华东地区监测">
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">监测地区</label>
                <select name="region_codes" multiple
                        class="w-full border rounded px-3 py-2 h-32">
                    <option value="110000">北京市</option>
                    <option value="310000">上海市</option>
                    <option value="440000">广东省</option>
                    <option value="320000">江苏省</option>
                    <option value="330000">浙江省</option>
                    <option value="370000">山东省</option>
                    <option value="410000">河南省</option>
                    <option value="510000">四川省</option>
                </select>
                <p class="text-xs text-gray-500 mt-1">按住 Ctrl/Cmd 多选</p>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">监测间隔（分钟）</label>
                <input type="number" name="interval_minutes" value="5" min="1"
                       class="w-32 border rounded px-3 py-2">
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">注册资本筛选（可选）</label>
                <input type="text" name="reg_cap"
                       class="w-full border rounded px-3 py-2"
                       placeholder="如：5000￥（表示5000万以上）">
            </div>

            <button type="submit"
                    class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                创建监测任务
            </button>
        </form>
    </div>

    <!-- Jobs Control Panel -->
    <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-xl font-semibold mb-4">任务控制</h2>

        <div id="jobs-list" class="space-y-3">
            <!-- Jobs will be loaded here -->
            <p class="text-gray-500">加载中...</p>
        </div>
    </div>

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow p-6">
            <div class="text-gray-500 text-sm">监测企业总数</div>
            <div class="text-2xl font-bold" id="stat-total">-</div>
        </div>
        <div class="bg-white rounded-lg shadow p-6">
            <div class="text-gray-500 text-sm">今日新增</div>
            <div class="text-2xl font-bold text-blue-600" id="stat-today">-</div>
        </div>
        <div class="bg-white rounded-lg shadow p-6">
            <div class="text-gray-500 text-sm">活跃配置</div>
            <div class="text-2xl font-bold text-green-600" id="stat-configs">-</div>
        </div>
        <div class="bg-white rounded-lg shadow p-6">
            <div class="text-gray-500 text-sm">待处理</div>
            <div class="text-2xl font-bold text-orange-600" id="stat-unprocessed">-</div>
        </div>
    </div>

    <!-- Companies Table -->
    <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold mb-4">监测结果</h2>

        <div class="overflow-x-auto">
            <table class="w-full">
                <thead>
                    <tr class="border-b">
                        <th class="text-left py-2">企业名称</th>
                        <th class="text-left py-2">信用代码</th>
                        <th class="text-left py-2">成立日期</th>
                        <th class="text-left py-2">注册资本</th>
                        <th class="text-left py-2">地区</th>
                        <th class="text-left py-2">监测时间</th>
                    </tr>
                </thead>
                <tbody id="companies-table">
                    <tr>
                        <td colspan="6" class="text-center py-4 text-gray-500">
                            加载中...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div id="pagination" class="mt-4 flex justify-center space-x-2">
            <!-- Pagination will be added here -->
        </div>
    </div>
</div>

<script>
// Token Configuration
document.getElementById('token-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        token: formData.get('token'),
        app_uuid: formData.get('app_uuid')
    };

    const response = await fetch('/api/monitoring/token', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    if (result.success) {
        alert('配置保存成功！');
        loadTokenConfig();
    } else {
        alert('保存失败: ' + result.error);
    }
});

document.getElementById('test-connection-btn').addEventListener('click', async () => {
    const response = await fetch('/api/monitoring/token/test', {
        method: 'POST'
    });
    const result = await response.json();
    alert(result.success ? result.message : '连接失败: ' + result.error);
});

// Monitoring Configuration
document.getElementById('monitoring-config-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const regionCodes = Array.from(document.querySelector('select[name="region_codes"]').selectedOptions)
                           .map(opt => opt.value);

    const data = {
        config_name: formData.get('config_name'),
        region_codes: regionCodes,
        interval_minutes: parseInt(formData.get('interval_minutes')),
        reg_cap: formData.get('reg_cap')
    };

    const response = await fetch('/api/monitoring/configs', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    if (result.success) {
        alert('监测配置创建成功！');
        e.target.reset();
        loadJobs();
    } else {
        alert('创建失败: ' + result.error);
    }
});

// Load functions
async function loadTokenConfig() {
    const response = await fetch('/api/monitoring/token');
    const result = await response.json();
    if (result.success) {
        document.getElementById('token-input').value = result.configs.token || '';
        document.getElementById('uuid-input').value = result.configs.app_uuid || '';
        document.getElementById('token-status').classList.remove('hidden');
        document.getElementById('status-text').textContent = '已配置';
    }
}

async function loadJobs() {
    const response = await fetch('/api/monitoring/jobs');
    const result = await response.json();
    const container = document.getElementById('jobs-list');

    if (result.jobs && result.jobs.length > 0) {
        container.innerHTML = result.jobs.map(job => `
            <div class="flex items-center justify-between p-3 border rounded">
                <div>
                    <div class="font-medium">${job.name}</div>
                    <div class="text-sm text-gray-500">
                        下次执行: ${job.next_run_time ? new Date(job.next_run_time).toLocaleString() : '已暂停'}
                    </div>
                </div>
                <div class="space-x-2">
                    <button onclick="runJobNow(${job.config_id})"
                            class="bg-green-500 text-white px-3 py-1 rounded text-sm hover:bg-green-600">
                        立即执行
                    </button>
                    <button onclick="toggleJob(${job.config_id})"
                            class="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600">
                        ${job.paused ? '恢复' : '暂停'}
                    </button>
                </div>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p class="text-gray-500">暂无监测任务</p>';
    }
}

async function runJobNow(configId) {
    if (!confirm('确定要立即执行此任务吗？')) return;

    const response = await fetch(`/api/monitoring/jobs/${configId}/run-now`, {
        method: 'POST'
    });
    const result = await response.json();
    alert(result.success ? result.message : '执行失败: ' + result.error);
    loadCompanies();
}

async function toggleJob(configId) {
    const response = await fetch(`/api/monitoring/jobs/${configId}/toggle`, {
        method: 'POST'
    });
    const result = await response.json();
    if (result.success) {
        loadJobs();
    } else {
        alert('操作失败: ' + result.error);
    }
}

async function loadStats() {
    const response = await fetch('/api/monitoring/stats');
    const result = await response.json();
    if (result.success) {
        document.getElementById('stat-total').textContent = result.stats.total_companies || 0;
        document.getElementById('stat-today').textContent = result.stats.today_added || 0;
        document.getElementById('stat-configs').textContent = result.stats.active_configs || 0;
        document.getElementById('stat-unprocessed').textContent = result.stats.unprocessed || 0;
    }
}

let currentOffset = 0;
const limit = 20;

async function loadCompanies(offset = 0) {
    currentOffset = offset;
    const response = await fetch(`/api/monitoring/companies?limit=${limit}&offset=${offset}`);
    const result = await response.json();
    const tbody = document.getElementById('companies-table');

    if (result.companies && result.companies.length > 0) {
        tbody.innerHTML = result.companies.map(company => `
            <tr class="border-b hover:bg-gray-50">
                <td class="py-2">${company.company_name}</td>
                <td class="py-2 text-sm text-gray-600">${company.credit_code || '-'}</td>
                <td class="py-2">${company.reg_date || '-'}</td>
                <td class="py-2">${company.reg_cap || '-'}</td>
                <td class="py-2">${company.region_name || '-'}</td>
                <td class="py-2 text-sm text-gray-600">
                    ${new Date(company.monitoring_time).toLocaleString()}
                </td>
            </tr>
        `).join('');

        // Update pagination
        updatePagination(result.total, offset);
    } else {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-500">暂无数据</td></tr>';
    }
}

function updatePagination(total, offset) {
    const container = document.getElementById('pagination');
    const totalPages = Math.ceil(total / limit);
    const currentPage = Math.floor(offset / limit) + 1;

    let html = '';

    if (currentPage > 1) {
        html += `<button onclick="loadCompanies(${offset - limit})" class="px-3 py-1 border rounded">上一页</button>`;
    }

    html += `<span class="px-3 py-1">第 ${currentPage} / ${totalPages} 页 (共 ${total} 条)</span>`;

    if (currentPage < totalPages) {
        html += `<button onclick="loadCompanies(${offset + limit})" class="px-3 py-1 border rounded">下一页</button>`;
    }

    container.innerHTML = html;
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    loadTokenConfig();
    loadJobs();
    loadStats();
    loadCompanies();
});

// Auto-refresh every 30 seconds
setInterval(() => {
    loadJobs();
    loadStats();
    loadCompanies(currentOffset);
}, 30000);
</script>
{% endblock %}
```

**Step 2: Add navigation link to base.html**

Check `code/templates/base.html` and add monitoring link:

```html
<!-- Add to navigation -->
<a href="/monitoring" class="text-gray-700 hover:text-gray-900 px-3 py-2">企业监测</a>
```

**Step 3: Commit**

```bash
git add code/templates/monitoring.html code/templates/base.html
git commit -m "feat: add monitoring management page with token/config/job controls"
```

---

## Task 8: Update database initialization

**Files:**
- Modify: `code/web_app.py`

**Step 1: Update get_db to initialize monitoring tables**

```python
def get_db():
    """获取数据库连接"""
    db = BOSSDatabase(str(DB_PATH))
    if db.connect():
        # 先初始化表（如果不存在）
        db.init_tables()
        # 添加升级列
        db.add_is_imported_column()
        db.add_discarded_column()
        # 初始化监测表
        db.init_monitoring_tables()
    return db
```

**Step 2: Commit**

```bash
git add code/web_app.py
git commit -m "feat: auto-initialize monitoring tables on startup"
```

---

## Task 9: Final Integration Testing

**Files:**
- None (manual testing)

**Step 1: Start the application**

```bash
cd /Users/rinzlacus/Downloads/Coding/boss-zhipin-web-ui
python code/web_app.py
```

Expected:
- Server starts on http://127.0.0.1:5001
- Scheduler initializes and starts
- Database tables created

**Step 2: Manual testing checklist**

Open browser to http://127.0.0.1:5001/monitoring

- [ ] Navigate to /monitoring page
- [ ] Configure RiskBird token
- [ ] Test token connection
- [ ] Create monitoring config
- [ ] Verify job appears in jobs list
- [ ] Run job manually
- [ ] Check monitored companies appear in table
- [ ] Verify stats update
- [ ] Wait for automatic execution (interval minutes)
- [ ] Pause/resume job
- [ ] Delete config

**Step 3: Check logs**

Verify scheduler logs:
```
✅ 后台任务调度器已启动
Added monitoring job: monitoring_1 (interval: 5 min)
Job monitoring_1 completed: {'success': True, 'companies_added': X}
```

**Step 4: Verify database**

```bash
sqlite3 data/boss_jobs.db "SELECT COUNT(*) FROM monitored_companies;"
sqlite3 data/boss_jobs.db "SELECT * FROM monitoring_configs;"
sqlite3 data/boss_jobs.db "SELECT config_key FROM riskbird_config;"
```

**Step 5: Commit final changes**

```bash
git add .
git commit -m "feat: complete enterprise monitoring module implementation"
```

---

## Summary

After completing all tasks, the enterprise monitoring module will be fully functional with:

✅ **Database Tables** - Token storage, monitoring configs, monitored companies
✅ **Token Management** - Encrypted storage, configuration UI, connection testing
✅ **Monitoring Service** - RiskBird API integration, data parsing, duplicate detection
✅ **Scheduler** - APScheduler integration for periodic execution
✅ **API Endpoints** - Complete REST API for all operations
✅ **Web Interface** - User-friendly monitoring management page
✅ **Testing** - Unit tests for core functionality

**Key Files Created:**
- `code/token_service.py` - Token encryption service
- `code/riskbird_monitor.py` - Monitoring core logic
- `code/templates/monitoring.html` - Management UI
- `tests/test_database_monitoring.py` - Database tests
- `tests/test_token_service.py` - Token service tests
- `tests/test_riskbird_monitor.py` - Monitor tests
- `tests/test_scheduler_integration.py` - Scheduler tests

**Key Files Modified:**
- `code/database.py` - Added monitoring tables and operations
- `code/web_app.py` - Integrated scheduler and API endpoints
- `code/riskbird_search.py` - Extracted reusable API functions
- `code/templates/base.html` - Added navigation link
- `requirements.txt` - Added APScheduler and cryptography

**Total Estimated Time:** 2-3 hours for complete implementation
