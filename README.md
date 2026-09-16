<img src="https://github.com/user-attachments/assets/96ff1fa2-83d8-4779-a956-4160f41fc967" alt="logo" width="75"/>

<section>
  <div>
    <h1>Hotel Reservation System API</h1>
    <p align="justify">
      This <b>API</b> was developed to showcase my backend development skills using
      <b>Python</b> and <b>Django REST Framework</b>. It provides a complete hotel reservation engine featuring robust authentication, room availability control, asynchronous background task execution, PDF voucher generation, and real-time WebSocket communication.
    </p>
    <p align="justify">
      The application implements full <b>CRUD</b> operations for user accounts, hotel properties, room management, and reservation lifecycles. Security and data integrity are handled through <b>JWT</b> authentication, custom field encryption (Fernet), and strict CORS middleware.
    </p>
    <p align="justify">
      Asynchronous processing and scheduled operations (such as automatic cancellation updates or report processing) are managed via <b>Celery</b> and <b>Redis</b>. OpenAPI/Swagger specifications are generated automatically using <b>drf-spectacular</b>.
    </p>
  </div>

  <div>
    <h2>Technologies</h2>
    <h4>Backend</h4>
    <ul>
      <li>Python 3.12</li>
      <li>Django 5.2.5</li>
      <li>Django REST Framework 3.16.1</li>
      <li>Django Channels 0.7.0 (ASGI / WebSockets)</li>
      <li>Daphne</li>
    </ul>
    <h4>Database & Cache</h4>
    <ul>
      <li>PostgreSQL</li>
      <li>Redis</li>
    </ul>
    <h4>Asynchronous Tasks</h4>
    <ul>
      <li>Celery 5.5.3</li>
      <li>django-celery-beat</li>
      <li>django-celery-results</li>
    </ul>
    <h4>Authentication & Security</h4>
    <ul>
      <li>djangorestframework-simplejwt (JWT)</li>
      <li>Cryptography (Fernet encryption)</li>
      <li>django-cors-headers</li>
    </ul>
    <h4>Document Generation</h4>
    <ul>
      <li>WeasyPrint</li>
      <li>xhtml2pdf</li>
    </ul>
    <h4>Documentation</h4>
    <ul>
      <li>drf-spectacular (Swagger UI & ReDoc)</li>
    </ul>
    <h4>Dependency Management & Tooling</h4>
    <ul>
      <li>uv 0.8.12</li>
      <li>Docker & Docker Compose</li>
      <li>Nginx</li>
    </ul>
    <h4>Tests</h4>
    <ul>
      <li>pytest 8.4.1</li>
    </ul>
  </div>

  <div>
    <h2>Services Used</h2>
    <ul>
      <li>GitHub</li>
    </ul>
  </div>

  <div>
    <h2>Getting Started</h2>
    <p align="justify">
      To clone this repository using <b>GitHub</b>, execute:

  ```bash
  git clone [https://github.com/seu-usuario/hotel_reservation_system_api.git](https://github.com/seu-usuario/hotel_reservation_system_api.git)
  cd hotel_reservation_system_api
  ```
  </p>

  <p align="justify">
    Create a <b>.env</b> file in the root directory with the following variables:

  ```env
  # Django Settings
  SECRET_KEY=your_secret_key_here
  DEBUG=True
  ALLOWED_HOSTS=localhost,127.0.0.1

  # Database (PostgreSQL)
  POSTGRES_DB=hotel_db
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=postgres
  POSTGRES_HOST=db
  POSTGRES_PORT=5432

  # Redis & Celery
  REDIS_URL=redis://redis:6379/0
  CELERY_BROKER_URL=redis://redis:6379/0

  # Field Encryption
  FIELD_ENCRYPTION_KEY=your_fernet_key_here
  ```
  </p>

  <h4>Running via Docker Compose (Recommended)</h4>
  <p align="justify">
    To build and start all containerized services (API, PostgreSQL, Redis, Celery worker/beat, Nginx), execute:

  ```bash
  docker compose -f docker-compose.prod.yml up -d --build
  ```
  </p>

  <p align="justify">
    Run database migrations inside the web container:

  ```bash
  docker compose -f docker-compose.prod.yml exec web python manage.py migrate
  ```
  </p>

  <h4>Running Locally with uv</h4>
  <p align="justify">
    Ensure you have <b>uv</b> installed. Sync dependencies and set up the virtual environment:

  ```bash
  uv sync
  ```
  </p>

  <p align="justify">
    Apply migrations and start the development server:

  ```bash
  uv run python manage.py migrate
  uv run python manage.py runserver
  ```
  </p>

  <p align="justify">
    To see the documentation made with <b>Swagger UI</b>, access:

    ```
    [http://127.0.0.1:8000/api/docs/swagger/](http://127.0.0.1:8000/api/docs/swagger/)
    ```
  </p>

  <p align="justify">
    To see the documentation made with <b>ReDoc</b>, access:

  ```
  [http://127.0.0.1:8000/api/docs/redoc/](http://127.0.0.1:8000/api/docs/redoc/)
  ```
  </p>

  <p align="justify">
    To run test suites using <b>pytest</b>:

  ```bash
  uv run pytest
  ```
  </p>
  </div>

  <div>
    <h2>Features</h2>
    <p>The main features of the application are:</p>
    <ul>
      <li>User Authentication & Accounts: Account management with JWT authentication and password reset workflows.</li>
      <li>Hotel & Room Management: Full CRUD for hotel properties, room categories, filtering, and availability management.</li>
      <li>Reservation Engine: Complete reservation workflow including booking creation, cancellation handling, and automated payment detail processing.</li>
      <li>PDF Voucher Generation: Automatic generation and rendering of reservation vouchers and cancellation notices using HTML templates.</li>
      <li>Asynchronous Processing: Background worker architecture using Celery and Redis for handling notifications and scheduled tasks.</li>
      <li>Real-time Updates: WebSocket integration via Django Channels and Daphne for live updates.</li>
      <li>OpenAPI Documentation: Automated interactive API documentation using OpenAPI 3.0 via drf-spectacular.</li>
    </ul>
  </div>

  <div>
    <h2>Authors</h2>
    <ul>
      <li>
        Eliezer Bergamo
      </li>
    </ul>
  </div>

  <div>
    <h2>Versioning</h2>
    <p>1.0.0</p>
  </div>

  <footer>
    <p align="center">All rights reserved &copy Eliezer Bergamo</p>
  </footer>
</section>
