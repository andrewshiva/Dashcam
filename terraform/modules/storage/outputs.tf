output "raw_video_bucket_name" {
  description = "Name of the raw video bucket"
  value       = google_storage_bucket.raw_video.name
}

output "validated_video_bucket_name" {
  description = "Name of the validated video bucket"
  value       = google_storage_bucket.validated_video.name
}

output "processed_bucket_name" {
  description = "Name of the processed bucket"
  value       = google_storage_bucket.processed_metadata.name
}
