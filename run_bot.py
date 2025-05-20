def send_email(title, url):
    if not (EMAIL_ADDRESS and EMAIL_PASSWORD and EMAIL_TO):
        print("✉️ Email config not set. Skipping.")
        return False
    try:
        recipients = [addr.strip() for addr in EMAIL_TO.split(",")]

        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS  # Visible To field
        msg["Bcc"] = ", ".join(recipients)  # Hidden recipients

        text = f"{title}\n\nWatch here: {url}"
        html = f"""\
        <html>
            <body>
                <h3>{title}</h3>
                <p><a href="{url}">▶ Watch Condensed Game</a></p>
                <p><i>{random.choice(COPY_LINES)}</i></p>
            </body>
        </html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipients, msg.as_string())

        print("✅ Email sent.")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False
