<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sandboxer</title>

    <style>
        :root {
            color-scheme: dark;
            --bg: #090b10;
            --panel: rgba(18, 22, 31, 0.78);
            --panel-hover: rgba(26, 32, 44, 0.95);
            --border: rgba(255, 255, 255, 0.08);
            --text: #f5f7fa;
            --muted: #8f9bad;
            --orange: #ff7a00;
            --yellow: #ffc400;
            --blue: #2496ed;
        }

        * {
            box-sizing: border-box;
        }

        html {
            min-height: 100%;
        }

        body {
            min-height: 100vh;
            margin: 0;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background:
                radial-gradient(circle at 50% 0%, rgba(255, 122, 0, 0.16), transparent 35%),
                radial-gradient(circle at 15% 80%, rgba(36, 150, 237, 0.12), transparent 30%),
                #090b10;
            color: var(--text);
            display: grid;
            place-items: center;
            padding: 48px 24px;
        }

        main {
            width: min(980px, 100%);
        }

        header {
            text-align: center;
            margin-bottom: 48px;
        }

        header img {
            display: block;
            width: 100%;
            max-width: 380px;
            height: auto;
            margin: 0 auto;
            filter: drop-shadow(0 18px 35px rgba(0, 0, 0, 0.35));
        }

        .links {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 18px;
        }

        .card {
            position: relative;
            min-height: 230px;
            padding: 26px;
            border: 1px solid var(--border);
            border-radius: 22px;
            background: var(--panel);
            backdrop-filter: blur(16px);
            text-decoration: none;
            color: inherit;
            overflow: hidden;
            transition:
                transform 180ms ease,
                border-color 180ms ease,
                background 180ms ease;
        }

        .card::before {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at top right, var(--glow), transparent 42%);
            opacity: 0.8;
            pointer-events: none;
        }

        .card:hover {
            transform: translateY(-6px);
            background: var(--panel-hover);
            border-color: rgba(255, 255, 255, 0.18);
        }

        .card.database {
            --glow: rgba(255, 196, 0, 0.14);
        }

        .card.laravel {
            --glow: rgba(255, 80, 80, 0.14);
        }

        .card.beamtic {
            --glow: rgba(36, 150, 237, 0.16);
        }

        .card.hedgedoc {
            --glow: rgba(72, 187, 120, 0.16);
        }

        .icon {
            position: relative;
            z-index: 1;
            width: 48px;
            height: 48px;
            border-radius: 14px;
            display: grid;
            place-items: center;
            margin-bottom: 42px;
            font-size: 1.35rem;
            font-weight: 900;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .card h2 {
            position: relative;
            z-index: 1;
            margin: 0 0 8px;
            font-size: 1.35rem;
        }

        .card p {
            position: relative;
            z-index: 1;
            margin: 0;
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.55;
        }

        .arrow {
            position: absolute;
            right: 22px;
            bottom: 20px;
            z-index: 1;
            font-size: 1.35rem;
            color: rgba(255, 255, 255, 0.45);
            transition:
                transform 180ms ease,
                color 180ms ease;
        }

        .card:hover .arrow {
            transform: translateX(4px);
            color: white;
        }

        footer {
            margin-top: 34px;
            text-align: center;
            color: #5f6877;
            font-size: 0.82rem;
        }

        @media (max-width: 760px) {
            .links {
                grid-template-columns: 1fr;
            }

            .card {
                min-height: 190px;
            }

            .icon {
                margin-bottom: 28px;
            }
        }
    </style>
</head>

<body>
    <main>
        <header>
            <img src="beamtic-sandboxer.png" alt="Beamtic Sandboxer">
        </header>

        <section class="links">
            <a class="card database" href="http://database.localhost">
                <div class="icon">DB</div>
                <h2>Database</h2>
                <p>Open the local database management interface.</p>
                <span class="arrow">→</span>
            </a>

            <a class="card laravel" href="http://laravel.localhost">
                <div class="icon">L</div>
                <h2>Laravel</h2>
                <p>Open the local Laravel development application.</p>
                <span class="arrow">→</span>
            </a>

            <a class="card laravel" href="http://hedgedoc.localhost/profundarium/">
                <div class="icon">P</div>
                <h2>Profundarium</h2>
                <p>Develop the public reading view for HedgeDoc notes.</p>
                <span class="arrow">→</span>
            </a>

            <a class="card hedgedoc" href="http://hedgedoc.localhost">
                <div class="icon">H</div>
                <h2>HedgeDoc</h2>
                <p>Open the local collaborative Markdown editor.</p>
                <span class="arrow">→</span>
            </a>

            <a class="card beamtic" href="https://beamtic.com">
                <div class="icon">B</div>
                <h2>Beamtic.com</h2>
                <p>Visit the main Beamtic website.</p>
                <span class="arrow">→</span>
            </a>
        </section>

        <footer>
            Beamtic Sandboxer
        </footer>
    </main>
</body>
</html>