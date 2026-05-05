---
name: playwright
description: Playwright E2E 测试、页面对象、fixture、视觉回归、可访问性测试和 CI 集成模式。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Playwright 技能

为构建完整的 Playwright E2E 测试套件提供专家级协助，包括页面对象、fixture、视觉回归和 CI/CD 集成。

## 能力

- 生成 Playwright 测试项目结构
- 创建页面对象模型，提升测试可维护性
- 实现自定义 fixture 和测试工具
- 配置视觉回归测试
- 使用 axe-core 设置可访问性测试
- 集成 CI/CD 流水线（GitHub Actions 等）
- 在 UI 测试之外生成 API 测试

## 使用场景

在需要完成以下任务时调用此技能：

- 为 Web 应用设置 Playwright 测试
- 创建页面对象模式来组织测试
- 实现视觉回归测试
- 配置跨浏览器测试
- 设置 CI/CD 测试自动化

## 输入

| 参数 | 类型 | 必填 | 描述 |
|-----------|------|----------|-------------|
| projectType | string | 否 | web、api、component（默认：web） |
| framework | string | 否 | react、nextjs、vue、angular |
| browsers | array | 否 | chromium、firefox、webkit（默认：全部） |
| features | array | 否 | visual、a11y、api、component |
| ci | string | 否 | github、gitlab、jenkins |

### 测试配置

```json
{
  "projectType": "web",
  "framework": "nextjs",
  "browsers": ["chromium", "firefox"],
  "features": ["visual", "a11y", "api"],
  "ci": "github",
  "baseUrl": "http://localhost:3000"
}
```

## 输出结构

```
tests/
├── playwright.config.ts           # Playwright 配置
├── fixtures/
│   ├── base.ts                    # 基础测试 fixture
│   ├── auth.ts                    # 认证 fixture
│   └── api.ts                     # API 辅助 fixture
├── pages/
│   ├── BasePage.ts                # 基础页面对象
│   ├── LoginPage.ts               # 登录页面对象
│   └── DashboardPage.ts           # 仪表盘页面对象
├── e2e/
│   ├── auth/
│   │   ├── login.spec.ts
│   │   └── logout.spec.ts
│   ├── dashboard/
│   │   └── dashboard.spec.ts
│   └── api/
│       └── users.api.spec.ts
├── visual/
│   ├── homepage.visual.spec.ts
│   └── screenshots/               # 基线截图
├── a11y/
│   └── accessibility.spec.ts
├── utils/
│   ├── helpers.ts
│   └── test-data.ts
└── .github/
    └── workflows/
        └── playwright.yml         # CI 工作流
```

## 生成代码模式

### Playwright 配置

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 13'] },
      dependencies: ['setup'],
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### 基础页面对象

```typescript
// tests/pages/BasePage.ts
import { Page, Locator, expect } from '@playwright/test';

export abstract class BasePage {
  readonly page: Page;
  readonly header: Locator;
  readonly footer: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.header = page.locator('header');
    this.footer = page.locator('footer');
    this.loadingSpinner = page.locator('[data-testid="loading"]');
  }

  abstract get url(): string;

  async goto() {
    await this.page.goto(this.url);
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.loadingSpinner.waitFor({ state: 'hidden' });
  }

  async expectToBeVisible() {
    await expect(this.page).toHaveURL(new RegExp(this.url));
  }

  async getToastMessage(): Promise<string | null> {
    const toast = this.page.locator('[role="alert"]');
    if (await toast.isVisible()) {
      return toast.textContent();
    }
    return null;
  }
}
```

### 登录页面对象

```typescript
// tests/pages/LoginPage.ts
import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class LoginPage extends BasePage {
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly forgotPasswordLink: Locator;

  constructor(page: Page) {
    super(page);
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: 'Sign in' });
    this.errorMessage = page.locator('[role="alert"]');
    this.forgotPasswordLink = page.getByRole('link', { name: 'Forgot password?' });
  }

  get url() {
    return '/login';
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectErrorMessage(message: string) {
    await expect(this.errorMessage).toContainText(message);
  }

  async expectLoginSuccess() {
    await expect(this.page).toHaveURL(/\/dashboard/);
  }
}
```

### 自定义 Fixture

```typescript
// tests/fixtures/base.ts
import { test as base, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';

interface TestFixtures {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
}

interface WorkerFixtures {
  authenticatedPage: void;
}

export const test = base.extend<TestFixtures, WorkerFixtures>({
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await use(loginPage);
  },

  dashboardPage: async ({ page }, use) => {
    const dashboardPage = new DashboardPage(page);
    await use(dashboardPage);
  },

  authenticatedPage: [
    async ({ browser }, use) => {
      const context = await browser.newContext({
        storageState: 'tests/.auth/user.json',
      });
      await use();
      await context.close();
    },
    { scope: 'worker' },
  ],
});

export { expect };
```

### 认证设置

```typescript
// tests/auth.setup.ts
import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.TEST_USER_EMAIL!);
  await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
  await page.getByRole('button', { name: 'Sign in' }).click();

  await expect(page).toHaveURL(/\/dashboard/);
  await page.context().storageState({ path: authFile });
});
```

### E2E 测试示例

```typescript
// tests/e2e/auth/login.spec.ts
import { test, expect } from '../../fixtures/base';

test.describe('Login', () => {
  test.beforeEach(async ({ loginPage }) => {
    await loginPage.goto();
  });

  test('should login with valid credentials', async ({ loginPage }) => {
    await loginPage.login('user@example.com', 'password123');
    await loginPage.expectLoginSuccess();
  });

  test('should show error with invalid credentials', async ({ loginPage }) => {
    await loginPage.login('invalid@example.com', 'wrongpassword');
    await loginPage.expectErrorMessage('Invalid email or password');
  });

  test('should show validation errors for empty fields', async ({ loginPage }) => {
    await loginPage.submitButton.click();
    await expect(loginPage.emailInput).toHaveAttribute('aria-invalid', 'true');
    await expect(loginPage.passwordInput).toHaveAttribute('aria-invalid', 'true');
  });
});
```

### 视觉回归测试

```typescript
// tests/visual/homepage.visual.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Visual Regression', () => {
  test('homepage should match snapshot', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveScreenshot('homepage.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('login page should match snapshot', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveScreenshot('login-page.png');
  });

  test('dashboard should match snapshot @authenticated', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveScreenshot('dashboard.png', {
      mask: [page.locator('[data-testid="user-avatar"]')],
    });
  });
});
```

### 可访问性测试

```typescript
// tests/a11y/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility', () => {
  test('homepage should have no accessibility violations', async ({ page }) => {
    await page.goto('/');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('login form should be keyboard accessible', async ({ page }) => {
    await page.goto('/login');

    await page.keyboard.press('Tab');
    await expect(page.getByLabel('Email')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByLabel('Password')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeFocused();
  });
});
```

### API 测试

```typescript
// tests/e2e/api/users.api.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Users API', () => {
  test('should get user list', async ({ request }) => {
    const response = await request.get('/api/users');

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.users).toBeInstanceOf(Array);
    expect(body.users.length).toBeGreaterThan(0);
  });

  test('should create a new user', async ({ request }) => {
    const response = await request.post('/api/users', {
      data: {
        name: 'Test User',
        email: 'test@example.com',
      },
    });

    expect(response.status()).toBe(201);

    const user = await response.json();
    expect(user.name).toBe('Test User');
    expect(user.email).toBe('test@example.com');
  });
});
```

### GitHub Actions 工作流

```yaml
# .github/workflows/playwright.yml
name: Playwright Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    timeout-minutes: 60
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright Browsers
        run: npx playwright install --with-deps

      - name: Run Playwright tests
        run: npx playwright test
        env:
          BASE_URL: ${{ secrets.BASE_URL }}
          TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
          TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30
```

## 依赖

```json
{
  "devDependencies": {
    "@playwright/test": "^1.50.0",
    "@axe-core/playwright": "^4.10.0"
  }
}
```

## 工作流

1. **设置配置** - 创建 playwright.config.ts
2. **创建页面对象** - 建模应用页面
3. **定义 fixture** - 设置测试工具
4. **编写测试** - E2E、视觉、可访问性测试
5. **配置 CI** - GitHub Actions 工作流
6. **生成报告** - HTML、JSON、JUnit

## 已应用的最佳实践

- 使用页面对象模型提升可维护性
- 使用自定义 fixture 提升复用性
- 并行执行测试
- 跨浏览器测试
- 视觉回归基线
- 集成可访问性测试
- 良好的测试隔离

## 参考资料

- Playwright 文档：https://playwright.dev/docs/intro
- playwright-skill：https://github.com/lackeyjb/playwright-skill
- mcp-playwright：https://github.com/executeautomation/mcp-playwright
- Axe-core：https://www.deque.com/axe/

## 目标流程

- e2e-testing-setup
- visual-regression-testing
- accessibility-testing
- api-testing
- ci-cd-integration
