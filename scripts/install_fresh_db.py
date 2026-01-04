
import os
import sys
from pathlib import Path

# Add parent to path to find other modules if needed
sys.path.append(str(Path(__file__).parent))

import db_tools

def get_mysql_command_base(config):
    """Build base mysql command list (without dbname) based on config"""
    cmd = ["mysql"]
    
    if config['socket']:
        cmd.extend(["--socket", config['socket']])
    else:
        cmd.extend(["-h", config['host']])
        cmd.extend(["-P", str(config['port'])])
        
    cmd.extend(["-u", config['user']])
    
    return cmd

def install_fresh_db():
    config = db_tools.load_config()
    db_name = config['dbname']
    
    print(f"⚠️  WARNING: This will DESTROY the database '{db_name}'.")
    print("Are you sure? (Type 'yes' to confirm)")
    
    # Simple safety check
    confirm = input("> ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        sys.exit(0)
        
    env = os.environ.copy()
    if config['password']:
        env['MYSQL_PWD'] = config['password']
        
    # 1. Drop and Recreate Database
    # We connect without a database selected initially or use -e to run command
    print(f"Resetting database '{db_name}'...")
    
    drop_create_sql = f"DROP DATABASE IF EXISTS {db_name}; CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    
    cmd_base = get_mysql_command_base(config)
    
    # Run Drop/Create
    create_cmd = cmd_base + ["-e", drop_create_sql]
    db_tools.run_command(" ".join(create_cmd), env)
    
    # 2. Import Schema
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_path}")
        sys.exit(1)
        
    print(f"Importing schema from {schema_path}...")
    
    # Build proper command: mysql ... dbname < schema.sql
    import_cmd_parts = cmd_base + [db_name]
    import_cmd_str = " ".join(import_cmd_parts) + f" < '{schema_path}'"
    
    db_tools.run_command(import_cmd_str, env)
    
    print("\n✅ Database installation complete!")

if __name__ == "__main__":
    install_fresh_db()
