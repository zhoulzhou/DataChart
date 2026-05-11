const initSqlJs = require('sql.js');
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');

const DB_PATH = path.join(__dirname, 'data.db');

let db = null;
let dirty = false;
let saveTimer = null;

function scheduleSave() {
  dirty = true;
  if (saveTimer) return;
  saveTimer = setTimeout(() => {
    saveTimer = null;
    if (dirty) saveDb();
  }, 300);
}

async function getDb() {
  if (db) return db;

  const SQL = await initSqlJs();

  if (fs.existsSync(DB_PATH)) {
    const buffer = fs.readFileSync(DB_PATH);
    db = new SQL.Database(buffer);
  } else {
    db = new SQL.Database();
  }

  db.run(`
    CREATE TABLE IF NOT EXISTS companies (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      short_name TEXT NOT NULL UNIQUE,
      status TEXT NOT NULL DEFAULT 'enabled',
      created_at TEXT DEFAULT (datetime('now','localtime'))
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS financial_reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL REFERENCES companies(id),
      year INTEGER NOT NULL,
      quarter INTEGER NOT NULL,
      created_at TEXT DEFAULT (datetime('now','localtime')),
      UNIQUE(company_id, year, quarter)
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS financial_fields (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      report_id INTEGER NOT NULL REFERENCES financial_reports(id),
      source TEXT NOT NULL,
      field_name TEXT NOT NULL,
      field_value REAL NOT NULL DEFAULT 0,
      field_alias TEXT
    )
  `);

  try {
    db.run("ALTER TABLE financial_fields ADD COLUMN field_alias TEXT");
  } catch (_) {}

  db.run(`
    CREATE TABLE IF NOT EXISTS admin_users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      password TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now','localtime'))
    )
  `);

  saveDb();

  const existing = queryAll("SELECT id FROM admin_users WHERE username = ?", ['admin']);
  if (existing.length === 0) {
    const hash = bcrypt.hashSync('admin123', 10);
    run("INSERT INTO admin_users (username, password) VALUES (?, ?)", ['admin', hash]);
    saveDb();
  }

  return db;
}

function saveDb() {
  if (!db) return;
  dirty = false;
  if (saveTimer) {
    clearTimeout(saveTimer);
    saveTimer = null;
  }
  const data = db.export();
  fs.writeFileSync(DB_PATH, Buffer.from(data));
}

function queryAll(sql, params = []) {
  const stmt = db.prepare(sql);
  if (params.length > 0) stmt.bind(params);
  const rows = [];
  while (stmt.step()) {
    rows.push(stmt.getAsObject());
  }
  stmt.free();
  return rows;
}

function queryOne(sql, params = []) {
  const rows = queryAll(sql, params);
  return rows.length > 0 ? rows[0] : null;
}

function run(sql, params = []) {
  db.run(sql, params);
  scheduleSave();
}

function forceSave() {
  if (dirty) saveDb();
}

module.exports = {
  getDb,
  queryAll,
  queryOne,
  run,
  saveDb,
  forceSave
};