#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <vector>
#include <tuple>
#include <variant>
#include <iostream>
#include <math.h>

namespace py = pybind11;

const double C_POS = 0.1;
const double C_NEG = 0.1;

struct Timestamp {
    uint sec;
    uint nsec;
};

struct Event {
    uint x;
    uint y;
    Timestamp ts;
    bool polarity;
};

Event cast_event(py::dict event_data)
{
    return Event {
        py::cast<uint>(event_data["x"]),
        py::cast<uint>(event_data["y"]),
        Timestamp {
            py::cast<uint>(event_data["ts"]["sec"]),
            py::cast<uint>(event_data["ts"]["nsec"])
        },
        py::cast<bool>(event_data["polarity"])
    };
}

void collect_events(std::vector<py::dict> events, double alpha, py::array_t<double> time_map_, py::array_t<double> image_)
{
    auto time_map = time_map_.mutable_unchecked();
    auto image = image_.mutable_unchecked();

    for(auto event_data : events)
    {   
        Event event = cast_event(event_data);

        auto tk = event.ts.sec + event.ts.nsec * 1e-9;
        auto dt = tk - time_map(event.y, event.x);
        auto c_th = event.polarity ? C_POS : -C_NEG;
        auto decay = std::exp(-alpha * dt);

        image(event.y, event.x) = decay * image(event.y, event.x) + c_th;
        time_map(event.y, event.x) = tk;
    }
}

PYBIND11_MODULE(integrator_cpp, m)
{
    m.def("collect_events", &collect_events);
}
