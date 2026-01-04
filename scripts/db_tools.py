
import os
import sys
import subprocess
import argparse
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from dotenv import load_dotenv

# Add parent dir to path to find api module if needed, 
# but mostly we just need the .env from there.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'api')
ENV_PATH = os.path.join(API_DIR, '.env')

def load_config():
    if os.path.exists(ENV_PATH):
        print(f"Loading environment from {ENV_PATH}")
        load_dotenv(ENV_PATH)
    else:
        print("Warning: .env file not found in api directory.")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in environment.")
        sys.exit(1)
    
    return parse_db_url(db_url)

def parse_db_url(url):
    # Format: mysql+pymysql://user:pass@host:port/dbname?option=value
    # Remove the driver prefix for standard parsing if present
    if url.startswith("mysql+pymysql://"):
        url = "mysql://" + url[16:]
    
    u = urlparse(url)
    
    config = {
        'user': u.username,
        'password': u.password,
        'host': u.hostname,
        'port': u.port or 3306,
        'dbname': u.path.lstrip('/'),
        'socket': None
    }
    
    # Check for socket in query
    qs = parse_qs(u.query)
    if 'unix_socket' in qs:
        config['socket'] = qs['unix_socket'][0]
        
    return config

def run_command(cmd, env=None):
    try:
        # Use shell=True for simple redirection handling, 
        # but manual redirection with subprocess is safer/cleaner usually.
        # However, for piping into/out of mysql, shell is easiest.
        subprocess.run(cmd, shell=True, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(1)

def backup(config, output_file=None):
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"backup_{config['dbname']}_{timestamp}.sql"
    
    print(f"Backing up database '{config['dbname']}' to '{output_file}'...")
    
    # Construct mysqldump command
    # Warning: Using -pPASSWORD on command line shows warnings.
    # Better to use MYSQL_PWD env var.
    
    env = os.environ.copy()
    if config['password']:
        env['MYSQL_PWD'] = config['password']
        
    cmd_parts = ["mysqldump"]
    
    if config['socket']:
        cmd_parts.extend(["--socket", config['socket']])
    else:
        cmd_parts.extend(["-h", config['host']])
        cmd_parts.extend(["-P", str(config['port'])])
        
    cmd_parts.extend(["-u", config['user']])
    
    # Add routines/events if you want full backup
    cmd_parts.extend(["--routines", "--events"])
    
    cmd_parts.append(config['dbname'])
    
    # Redirection
    cmd_str = " ".join(cmd_parts) + f" > {output_file}"
    
    run_command(cmd_str, env)
    print("Backup successful!")

def restore(config, input_file):
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
        
    print(f"Restoring database '{config['dbname']}' from '{input_file}'...")
    print("WARNING: This will overwrite existing data. Proceeding in 3 seconds...")
    import time
    time.sleep(3)
    
    env = os.environ.copy()
    if config['password']:
        env['MYSQL_PWD'] = config['password']
        
    cmd_parts = ["mysql"]
    
    if config['socket']:
        cmd_parts.extend(["--socket", config['socket']])
    else:
        cmd_parts.extend(["-h", config['host']])
        cmd_parts.extend(["-P", str(config['port'])])
        
    cmd_parts.extend(["-u", config['user']])
    cmd_parts.append(config['dbname'])
    
    # Input redirection
    cmd_str = " ".join(cmd_parts) + f" < {input_file}"
    
    run_command(cmd_str, env)
    print("Restore successful!")

def main():
    parser = argparse.ArgumentParser(description="Database Backup & Restore Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Backup
    parser_backup = subparsers.add_parser("backup", help="Backup database to SQL file")
    parser_backup.add_argument("-o", "--output", help="Output filename (optional)")
    
    # Restore
    parser_restore = subparsers.add_parser("restore", help="Restore database from SQL file")
    parser_restore.add_argument("input", help="Input SQL file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    config = load_config()
    
    if args.command == "backup":
        backup(config, args.output)
    elif args.command == "restore":
        restore(config, args.input)

if __name__ == "__main__":
    main()
