# ---- Build Stage ----
# Use a base image with the GCC compiler
FROM gcc:15.2-trixie AS builder

# Set the working directory
WORKDIR /usr/src/app

# Copy the C++ source file
COPY ./cpp/main.cpp .

# Compile the C++ application into a static executable
# The -static flag bundles libraries into the executable, making it portable
RUN g++ -o prime-calculator main.cpp -static


# ---- Final Stage ----
# Use a minimal base image
FROM scratch

# Set the working directory
WORKDIR /app

# Copy the compiled binary from the builder stage
COPY --from=builder /usr/src/app/prime-calculator .

# Command to run the application when the container starts
CMD ["./prime-calculator"]
