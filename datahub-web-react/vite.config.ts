import { codecovVitePlugin } from '@codecov/vite-plugin';
import react from '@vitejs/plugin-react-swc';
import * as path from 'path';
import { defineConfig, loadEnv } from 'vite';
import macrosPlugin from 'vite-plugin-babel-macros';
import svgr from 'vite-plugin-svgr';

const injectMeticulous = () => {
    if (!process.env.REACT_APP_METICULOUS_PROJECT_TOKEN) {
        return null;
    }

    return {
        name: 'inject-meticulous',
        transformIndexHtml: {
            transform(html) {
                const scriptTag = `
                    <script
                        data-recording-token=${process.env.REACT_APP_METICULOUS_PROJECT_TOKEN}
                        src="https://snippet.meticulous.ai/v1/meticulous.js">
                    </script>
                `;

                return html.replace('</head>', `${scriptTag}\n</head>`);
            },
        },
    };
};

// https://vitejs.dev/config/
export default defineConfig(async ({ mode }) => {
    const { viteStaticCopy } = await import('vite-plugin-static-copy');

    // Via https://stackoverflow.com/a/66389044.
    const env = loadEnv(mode, process.cwd(), '');
    process.env = { ...process.env, ...env };

    const themeConfigFile = `./src/conf/theme/${process.env.REACT_APP_THEME_CONFIG}`;
    // eslint-disable-next-line global-require, import/no-dynamic-require, @typescript-eslint/no-var-requires
    const themeConfig = require(themeConfigFile);

    // Setup proxy to the datahub-frontend service.
    const frontendProxy = {
        target: process.env.REACT_APP_PROXY_TARGET || 'http://localhost:9002',
        changeOrigin: true,
    };
    // Setup proxy to the AI Assistant service (datahub-actions).
    const aiAssistantProxy = {
        target: 'http://localhost:8082',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/ai-assistant/, ''),
    };
    const proxyOptions = {
        '/logIn': frontendProxy,
        '/authenticate': frontendProxy,
        '/api/v2/graphql': frontendProxy,
        '/openapi/v1/tracking/track': frontendProxy,
        '/api/ai-assistant': aiAssistantProxy,
    };

    const devPlugins = mode === 'development' ? [injectMeticulous()] : [];

    return {
        appType: 'spa',
        plugins: [
            ...devPlugins,
            react(),
            svgr(),
            macrosPlugin(),
            viteStaticCopy({
                targets: [
                    // Self-host images by copying them to the build directory
                    { src: 'src/images/*', dest: 'assets/platforms' },
                    // Also keep the theme json files in the build directory
                    { src: 'src/conf/theme/*.json', dest: 'assets/conf/theme' },
                ],
            }),
            viteStaticCopy({
                targets: [
                    // Copy monaco-editor files to the build directory
                    // Because of the structured option, specifying dest .
                    // means that it will mirror the node_modules/... structure
                    // in the build directory.
                    {
                        src: 'node_modules/monaco-editor/min/vs/',
                        dest: '.',
                    },
                    {
                        src: 'node_modules/monaco-editor/min-maps/vs/',
                        dest: '.',
                        rename: (name, ext, fullPath) => {
                            console.log(name, ext, fullPath);
                            return name;
                        },
                    },
                ],
                structured: true,
            }),
            codecovVitePlugin({
                enableBundleAnalysis: true,
                bundleName: 'datahub-react-web',
                uploadToken: process.env.CODECOV_TOKEN,
                gitService: 'github',
            }),
        ],
        // optimizeDeps: {
        //     include: ['@ant-design/colors', '@ant-design/icons', 'lodash-es', '@ant-design/icons/es/icons'],
        // },
        envPrefix: 'REACT_APP_',
        build: {
            outDir: 'dist',
            target: 'esnext',
            minify: 'esbuild',
            reportCompressedSize: false,
        },
        server: {
            open: false,
            host: true,  // Listen on all network interfaces (allows Docker to connect)
            port: 3000,
            proxy: proxyOptions,
        },
        css: {
            preprocessorOptions: {
                less: {
                    javascriptEnabled: true,
                    // Override antd theme variables.
                    // https://4x.ant.design/docs/react/customize-theme#Ant-Design-Less-variables
                    modifyVars: themeConfig.styles,
                },
            },
        },
        test: {
            globals: true,
            environment: 'jsdom',
            setupFiles: './src/setupTests.ts',
            css: true,
            // reporters: ['verbose'],
            coverage: {
                enabled: true,
                provider: 'v8',
                reporter: ['text', 'json', 'html'],
                include: ['src/**/*.ts'],
                reportsDirectory: '../build/coverage-reports/datahub-web-react/',
                exclude: [],
            },
        },
        resolve: {
            alias: {
                // Root Directories
                '@src': path.resolve(__dirname, 'src'),
                '@app': path.resolve(__dirname, 'src/app'),
                '@conf': path.resolve(__dirname, 'src/conf'),
                '@components': path.resolve(__dirname, 'src/alchemy-components'),
                '@graphql': path.resolve(__dirname, 'src/graphql'),
                '@graphql-mock': path.resolve(__dirname, 'src/graphql-mock'),
                '@images': path.resolve(__dirname, 'src/images'),
                '@providers': path.resolve(__dirname, 'src/providers'),
                '@utils': path.resolve(__dirname, 'src/utils'),

                // Specific Files
                '@types': path.resolve(__dirname, 'src/types.generated.ts'),
            },
        },
    };
});
