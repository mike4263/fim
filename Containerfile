# Stage 1: Build the application
FROM rust:1.82 AS builder

# Set the working directory inside the container
WORKDIR /usr/src/fim

# Copy the Cargo.toml and Cargo.lock files
COPY Cargo.toml Cargo.lock ./

# Copy the source code
COPY src ./src
COPY .sqlx ./.sqlx
COPY db ./db

# Build the application in release mode
RUN cargo build --release

# Stage 2: Create a minimal image for running the app
FROM fedora:latest

# Copy the binary from the builder stage
COPY --from=builder /usr/src/fim/target/release/fim /usr/local/bin/fim

RUN mkdir /app && chmod 777 /app
ENV FIM_DB_URL=/app/fim.db

# Specify the command to run the executable
ENTRYPOINT ["fim"]