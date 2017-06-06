//
//  file_util.cpp
//  rail-tools
//
//  Created by Ben Langmead on 5/21/17.
//  Copyright © 2017 jhu. All rights reserved.
//

#include <cstdlib>
#include <sys/stat.h>
#include "file_util.hpp"

namespace rail {

bool exists(const std::string& fn) {
	struct stat buf;
	return stat(fn.c_str(), &buf) == 0;
}

bool exists_and_executable(const std::string& fn) {
	struct stat buf;
	return (stat(fn.c_str(), &buf) == 0) && (buf.st_mode & S_IXUSR);
}

std::string make_temp_dir(const std::string& scratch) {
	if(!scratch.empty()) {
	}
	char plate[] = "railtmpXXXXXX";
	return ::mkdtemp(plate);
}

}  // namespace rail
