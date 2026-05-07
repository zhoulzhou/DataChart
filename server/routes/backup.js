const express = require('express')
const fs = require('fs')
const path = require('path')
const { authMiddleware } = require('../middleware/auth')

const router = express.Router()
router.use(authMiddleware)

const BACKUP_DIR = '/data/fi_db_backup'
const DB_PATH = path.join(__dirname, '..', 'data.db')

function ensureBackupDir() {
  if (!fs.existsSync(BACKUP_DIR)) {
    fs.mkdirSync(BACKUP_DIR, { recursive: true })
  }
}

function pad(n) {
  return String(n).padStart(2, '0')
}

router.post('/create', (_req, res) => {
  try {
    if (!fs.existsSync(DB_PATH)) {
      return res.json({ code: 1, message: '数据库文件不存在' })
    }

    ensureBackupDir()

    const now = new Date()
    const name = `data_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}.db`
    const dest = path.join(BACKUP_DIR, name)

    fs.copyFileSync(DB_PATH, dest)
    res.json({ code: 0, message: '备份成功', data: { name } })
  } catch (err) {
    res.json({ code: 1, message: '备份失败: ' + err.message })
  }
})

router.get('/list', (_req, res) => {
  try {
    ensureBackupDir()

    const files = fs.readdirSync(BACKUP_DIR)
      .filter(f => f.startsWith('data_') && f.endsWith('.db'))
      .map(f => {
        const fullPath = path.join(BACKUP_DIR, f)
        const stat = fs.statSync(fullPath)
        return {
          name: f,
          size: stat.size,
          sizeStr: (stat.size / 1024).toFixed(1) + ' KB',
          time: stat.mtime.toISOString(),
          timeStr: stat.mtime.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
        }
      })
      .sort((a, b) => b.time.localeCompare(a.time))
      .slice(0, 10)

    res.json({ code: 0, data: files, message: 'ok' })
  } catch (err) {
    res.json({ code: 1, message: err.message })
  }
})

module.exports = router
