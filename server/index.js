const express = require('express');
const cors = require('cors');
const path = require('path');
const { getDb, forceSave } = require('./db');

const authRoutes = require('./routes/auth');
const companiesRoutes = require('./routes/companies');
const financialsRoutes = require('./routes/financials');
const backupRoutes = require('./routes/backup');
const fetchRoutes = require('./routes/fetch');

const { JWT_SECRET } = require('./middleware/auth');

if (!process.env.JWT_SECRET) {
  console.warn('[WARN] JWT_SECRET 未设置，使用默认值，生产环境请设置环境变量');
}
const PORT = 3001;

const app = express();

app.use(cors());
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/companies', companiesRoutes);
app.use('/api/financials', financialsRoutes);
app.use('/api/backup', backupRoutes);
app.use('/api/fetch-financials', fetchRoutes);

const publicCompaniesRoutes = require('./routes/companies').publicRouter;
const publicFinancialsRoutes = require('./routes/financials').publicRouter;

app.use('/api/public/companies', publicCompaniesRoutes);
app.use('/api/public/financials', publicFinancialsRoutes);

app.get('/api/health', (_req, res) => {
  res.json({ code: 0, message: 'ok' });
});

app.use(express.static(path.join(__dirname, '../client/dist')));
app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, '../client/dist/index.html'));
});

getDb().then(() => {
  app.listen(PORT, '127.0.0.1', () => {
    console.log(`Server running on http://127.0.0.1:${PORT}`);
  });
}).catch(err => {
  console.error('Failed to initialize database:', err);
  process.exit(1);
});

process.on('SIGINT', () => { forceSave(); process.exit(); });
process.on('SIGTERM', () => { forceSave(); process.exit(); });
