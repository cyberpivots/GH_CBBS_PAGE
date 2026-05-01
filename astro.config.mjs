import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

const repositoryBase = '/GH_CBBS_PAGE';

export default defineConfig({
  site: 'https://cyberpivots.github.io',
  base: repositoryBase,
  output: 'static',
  integrations: [
    sitemap({
      namespaces: {
        news: false,
        video: false
      }
    })
  ],
  image: {
    layout: 'constrained'
  }
});

