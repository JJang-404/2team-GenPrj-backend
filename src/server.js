import path from 'path';
import { fileURLToPath } from 'url';
import cors from 'cors';
import dotenv from 'dotenv';
import express from 'express';
import editorRoutes from './routes/editorRoutes.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const app = express();
const port = Number(process.env.PORT || 4000);
const host = process.env.APP_HOST || '127.0.0.1';

app.use(cors());
app.use(express.json({ limit: '100mb' }));
app.use('/api', editorRoutes);

app.listen(port, host, () => {
  console.log(`Demo backend listening on http://${host}:${port}`);
});
