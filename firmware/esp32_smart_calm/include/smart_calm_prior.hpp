#pragma once

#include <array>

#include "smart_calm_types.hpp"

namespace smart_calm {

inline constexpr std::array<PriorEntry, 9> kSmartCalmPrior = {{
    {0, 0, -0.53968084f},
    {0, 1, 4.2750745f},
    {1, 0, 2.2942858f},
    {1, 1, 2.2902391f},
    {1, 2, 1.3158103f},
    {3, 0, 4.0038934f},
    {3, 1, 3.7657652f},
    {3, 2, 4.9773564f},
    {5, 0, 2.9675798f},
}};

}  // namespace smart_calm

