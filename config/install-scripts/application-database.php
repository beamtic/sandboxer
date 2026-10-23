<?php
// Runs once after MariaDB is healthy, including when its data already exists.
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
$prefix = $argv[1] ?? '';
if (!in_array($prefix, ['WORDPRESS', 'HEDGEDOC'], true)) {
    throw new RuntimeException('Choose WORDPRESS or HEDGEDOC database settings.');
}
$name = getenv($prefix . '_DB_NAME');
$user = getenv($prefix . '_DB_USER');
$password = getenv($prefix . '_DB_PASSWORD');
if (!preg_match('/^[A-Za-z0-9_]{1,64}$/D', $name ?: '') ||
    !preg_match('/^[A-Za-z0-9_]{1,80}$/D', $user ?: '') || $password === false || $password === '') {
    throw new RuntimeException('Set a simple application database name, user, and nonempty password.');
}
$db = new mysqli('db', 'root', getenv('MYSQL_ROOT_PASSWORD'));
// Use a known quoting mode before escaping the account password.
$db->query("SET SESSION sql_mode = ''");
$quotedPassword = $db->real_escape_string($password);
$db->query("CREATE DATABASE IF NOT EXISTS `$name` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
$db->query("CREATE USER IF NOT EXISTS '$user'@'%' IDENTIFIED BY '$quotedPassword'");
// Underscores are wildcards in database-level grants unless escaped.
$grantName = str_replace('_', '\\_', $name);
$db->query("GRANT ALL PRIVILEGES ON `$grantName`.* TO '$user'@'%'");
// Existing passwords are preserved; verify them before reporting success.
$check = new mysqli('db', $user, $password, $name);
echo "$prefix database ready.\n";
