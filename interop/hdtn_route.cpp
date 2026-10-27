// Ask HDTN's contact graph routing (common/cgr, as HDTN's router calls it) for the best
// route through a contact plan.
//
//   hdtn_route <hdtn.json> <source> <dest> <time> [<time> ...]
//
// Prints one line per time: "<time> <next hop> <best_delivery_time> <arrival> <hops>" or
// "<time> none".
#include <iostream>
#include <string>
#include "libcgr.h"

int main(int argc, char **argv) {
    if (argc < 5) {
        std::cerr << "usage: hdtn_route <hdtn.json> <source> <dest> <time>...\n";
        return 2;
    }
    const std::vector<cgr::Contact> plan = cgr::cp_load(argv[1]);
    const cgr::nodeId_t source = std::stoull(argv[2]), dest = std::stoull(argv[3]);
    for (int i = 4; i < argc; i++) {
        const time_t t = std::stoll(argv[i]);
        // Same root contact as HDTN's router (module/router/src/router.cpp)
        cgr::Contact root(source, source, 0, cgr::MAX_TIME_T, 100, 1.0, 0);
        root.arrival_time = t;
        cgr::Route r = cgr::dijkstra(&root, dest, plan);
        if (!r.valid()) {
            std::cout << t << " none\n";
            continue;
        }
        // best_delivery_time is computed from contact start times only (Route::refresh_metrics),
        // so it can be earlier than t; the search's arrival time at the last hop is printed too
        std::cout << t << " " << r.next_node << " " << r.best_delivery_time << " "
                  << r.get_last_contact().arrival_time << " ";
        bool first = true;
        for (const cgr::Contact &c : r.get_hops()) {
            std::cout << (first ? "" : ",") << c.frm << ">" << c.to << "@" << c.start;
            first = false;
        }
        std::cout << "\n";
    }
    return 0;
}
