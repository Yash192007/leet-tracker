# LeetCode Class Tracker

## Deployment

### Docker

Build:

```
docker build -t leetcode-class-tracker .
```

Run:

```
docker run -p 5000:5000 -e ADMIN_USERNAME=admin -e ADMIN_PASSWORD=admin123 leetcode-class-tracker
```

### Environment variables

- `SECRET_KEY`: Flask secret key
- `ADMIN_USERNAME`: admin login username
- `ADMIN_PASSWORD`: admin login password
- `PORT`: port to run on (default `5000`)
- `FLASK_DEBUG`: `1` to enable debug mode

### Heroku via GitHub

1. Create a GitHub repository and push your project:

```
git init
git add .
git commit -m "Initial tracker app"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

2. Create a Heroku app:

```
heroku create <your-heroku-app-name>
```

3. In GitHub, add repository secrets:
- `HEROKU_API_KEY` — your Heroku API key
- `HEROKU_APP_NAME` — your Heroku app name

4. Push to GitHub. The workflow at `.github/workflows/heroku-deploy.yml` will deploy automatically.

5. Set config vars on Heroku:

```
heroku config:set ADMIN_USERNAME=admin ADMIN_PASSWORD=admin123 SECRET_KEY=some-secret
```

6. Open the app:

```
heroku open
```

### GitHub Actions deployment

The project includes a GitHub Actions workflow that deploys to Heroku on every push to `main`.
