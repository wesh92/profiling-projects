#include <iostream>
#include <cmath>
#include <cstdlib>
#include <chrono>

// Function to check if a number is prime
bool isPrime(int n) {
    if (n <= 1) return false;
    for (int i = 2; i <= sqrt(n); ++i) {
        if (n % i == 0) return false;
    }
    return true;
}

int main() {
    // Get the upper limit from an environment variable, or use a default
    const char* max_prime_str = std::getenv("MAX_PRIME");
    int max_prime = (max_prime_str != nullptr) ? std::atoi(max_prime_str) : 500000;

    std::cout << "Starting prime number calculation up to " << max_prime << std::endl;
    auto start = std::chrono::high_resolution_clock::now();

    int primes_found = 0;
    for (int i = 1; i <= max_prime; ++i) {
        if (isPrime(i)) {
            primes_found++;
        }
        // Log progress every 50,000 numbers
        if (i % 50000 == 0) {
            std::cout << "Checked up to " << i << "..." << std::endl;
        }
    }

    auto stop = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(stop - start);

    std::cout << "Calculation finished in " << duration.count() << " seconds." << std::endl;
    std::cout << "Found " << primes_found << " prime numbers." << std::endl;

    return 0;
}
