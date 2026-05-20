resource "google_pubsub_topic" "raw" {
  name = var.pubsub_topic
}

resource "google_pubsub_topic" "dead_letter" {
  name = "${var.pubsub_topic}-dead-letter"
}

resource "google_pubsub_subscription" "writer" {
  name  = "bicing-writer-sub"
  topic = google_pubsub_topic.raw.id

  # Push to bicing_writer Cloud Function URL (filled in after CF is deployed)
  push_config {
    push_endpoint = google_cloudfunctions2_function.writer.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.writer.email
    }
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  depends_on = [
    google_pubsub_topic_iam_member.dead_letter_publisher,
  ]
}

# Allow Pub/Sub to publish to the dead-letter topic
resource "google_pubsub_topic_iam_member" "dead_letter_publisher" {
  topic  = google_pubsub_topic.dead_letter.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Allow Pub/Sub to ack messages on the main subscription (needed for dead-letter)
resource "google_pubsub_subscription_iam_member" "dead_letter_subscriber" {
  subscription = google_pubsub_subscription.writer.id
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

data "google_project" "project" {}
