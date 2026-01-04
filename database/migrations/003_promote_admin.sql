-- Promote user to admin
-- Replace 'dan' or 'dmolloy@my.com' with the actual username/email if different
UPDATE users SET role = 'admin' WHERE username = 'dan' OR email = 'dmolloy@my.com';
