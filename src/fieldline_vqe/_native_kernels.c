#include <stddef.h>
#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
EXPORT double weighted_parity(const unsigned char *odd_flags, const double *weights, size_t n) {
    double total = 0.0;
    double signed_sum = 0.0;
    size_t i;
    for (i = 0; i < n; ++i) {
        double w = weights[i];
        total += w;
        signed_sum += odd_flags[i] ? -w : w;
    }
    return total <= 0.0 ? 0.0 : signed_sum / total;
}
EXPORT void sector_mask(const unsigned char *odd_flags, unsigned char *mask, size_t n, int want_even) {
    size_t i;
    for (i = 0; i < n; ++i) {
        unsigned char is_even = odd_flags[i] ? 0 : 1;
        mask[i] = (unsigned char)(is_even == (want_even ? 1 : 0));
    }
}
