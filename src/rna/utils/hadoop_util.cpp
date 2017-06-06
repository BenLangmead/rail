//
//  hadoop_util.cpp
//  rail-tools
//
//  Created by Ben Langmead on 5/21/17.
//  Copyright © 2017 jhu. All rights reserved.
//

#include <cstdlib>
#include "hadoop_util.hpp"

namespace rail {

std::string get_task_partition() {
	const char* env_p = std::getenv("mapred_task_partition");
	if(env_p == NULL) {
		env_p = std::getenv("mapreduce_task_partition");
		if(env_p == NULL) {
			return "0";
		}
	}
	return std::string(env_p);
}

}  // namespace rail
