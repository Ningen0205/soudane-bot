import psycopg2

connection = psycopg2.connect(
    host="db", user="postgres", password="password", database="soudane_bot"
)

with connection:
    with connection.cursor() as cursor:
        sql = "INSERT INTO users (email, password) VALUES (%s, %s)"
        cursor.execute(sql, ("test@example.com", "very-secret"))

    connection.commit()
