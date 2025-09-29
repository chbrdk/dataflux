#!/bin/bash
# Create Kafka topics for DataFlux

set -e

echo "Creating Kafka topics for DataFlux..."

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
sleep 30

# Create topics
echo "Creating asset-processing topic..."
kafka-topics --create \
  --topic asset-processing \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=604800000 \
  --config segment.ms=3600000

echo "Creating analysis-results topic..."
kafka-topics --create \
  --topic analysis-results \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=604800000

echo "Creating feedback-events topic..."
kafka-topics --create \
  --topic feedback-events \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=2592000000

echo "Creating system-events topic..."
kafka-topics --create \
  --topic system-events \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=604800000

echo "Creating search-analytics topic..."
kafka-topics --create \
  --topic search-analytics \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=2592000000

echo "Listing all topics..."
kafka-topics --list --bootstrap-server localhost:9092

echo "Kafka topics created successfully!"
