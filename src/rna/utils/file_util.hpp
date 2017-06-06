//
//  file_util.hpp
//  rail-tools
//
//  Created by Ben Langmead on 5/21/17.
//  Copyright © 2017 jhu. All rights reserved.
//

#ifndef file_util_hpp
#define file_util_hpp

#include <string>

namespace rail {

bool exists(const std::string& fn);

bool exists_and_executable(const std::string& fn);

std::string make_temp_dir(const std::string& scratch);

}  // namespace rail

#endif /* file_util_hpp */
