FROM node:24.21.0-alpine3.24 AS build
# Native modules are built against the same Alpine/musl runtime used below.
RUN apk add --no-cache git python3 make g++
ARG HEDGEDOC_REF=90212dc04003741393d19b2c90a4cba2f81b8a7b
WORKDIR /hedgedoc
RUN git init . && git remote add origin https://github.com/Turbulentarius/hedgedoc.git \
    && git fetch --depth=1 origin "${HEDGEDOC_REF}" && git checkout --detach FETCH_HEAD
ENV npm_config_nodedir=/usr/local
RUN node .yarn/releases/yarn-4.13.0.cjs install --immutable
RUN node .yarn/releases/yarn-4.13.0.cjs build > /tmp/webpack.log 2>&1 \
    || { tail -n 80 /tmp/webpack.log; exit 1; }
RUN node .yarn/releases/yarn-4.13.0.cjs workspaces focus --production \
    && rm -rf .git .yarn/cache .yarn/install-state.gz

FROM node:24.21.0-alpine3.24
# Match the account owning the existing Sandboxer HedgeDoc volume.
RUN addgroup -g 10000 hedgedoc && adduser -D -u 10000 -G hedgedoc hedgedoc
RUN mkdir -p /data/uploads && chown -R hedgedoc:hedgedoc /data
WORKDIR /hedgedoc
COPY ./config/hedgedoc/config.json /hedgedoc/config.json
COPY --from=build --chown=hedgedoc:hedgedoc /hedgedoc /hedgedoc
ENV NODE_ENV=production
USER hedgedoc
EXPOSE 3000
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=12 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/status',r=>{r.resume();process.exit(r.statusCode===200?0:1)}).on('error',()=>process.exit(1))"
CMD ["node", "app.js"]
