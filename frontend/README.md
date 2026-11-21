# Smart Parking: вебінтерфейс

## Демонстрація адаптивних вимірювань

```powershell
npm ci
npm run dev
```

Відкрийте `/measurements` на адресі Vite. У меню карти це пункт «Вимірювання».
Сторінка використовує відкриті записи City of Melbourne за 2019 рік і працює
самостійно, без входу, API, бази даних або підключеного фізичного пристрою.
Карта й керування системою зберігають свої звичайні умови доступу.

- Виберіть одне з трьох місць, запустіть відтворення або натискайте «Наступний вимір».
- На графіку видно записаний стан, щохвилинний і адаптивний покази; крапки є вимірюваннями, затінення є часом неправильного показу.
- У «Останньому рішенні» показано виміряний стан, обрану паузу, спостережену історію та час наступної перевірки.
- «Чому обрано саме цю паузу?» розкриває оцінки очікуваної помилки та витрат для всіх допустимих пауз.
- Журнал можна зберегти в CSV. Він містить виконані виміри обох розкладів у вже відтвореній частині фрагмента.
- Результат дослідження на 867 місцях показано окремо від лічильників поточного прикладу.

```powershell
npm run test:sampling
npm run build
npm run lint
```

Тести перевірено на Node.js 22.23.2 з його вбудованою підтримкою TypeScript.
`test:sampling` звіряє розподіл таблиць для 867 місць, 384 граничні контексти,
три повні траси й часові помилки з незалежними результатами Python.

Дані демонстрації: `public/data/sampling-demo.json`. Контрольні траси, які не входять
у клієнтський застосунок: `tests/fixtures/sampling-demo-golden.json`.
Для повторного експорту з наявних дослідницьких артефактів запустіть із кореня
репозиторію `python research/parking_sampling/export_demo.py` у середовищі
з `research/parking_sampling/requirements.txt`. Скрипт перевіряє контрольні суми,
читає готові таблиці та записи, не запускає навчання чи повторний добір параметрів.

Докладний опис фази: [phase5-demo.md](../docs/research/adaptive-sampling/phase5-demo.md).

## Довідка початкового шаблону Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
