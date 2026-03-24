$fn=96;
include <BOSL2/std.scad>
include <BOSL2/screws.scad>


assembly();
//lens_hold();  
//bottom_hold();
//ring();
//nut();
//up_hold(); 
// projection() bl();
//translate([0,0, 0]) bl_hold();
//color("silver", 0.8) translate([0,8,0]) bl();
//knob();  
//phone_holder(); 
//stencil();
 
//film();
//film_frame(4); 
//  translate([0,0, 2]) film_frame_cup(4); 
 
module assembly()
{
  translate([0,0, 30]) bolt();
  translate([0,0, 66]) rotate([180,0,0]) nut();
  
  translate([0,0, 85]) color("red", 0.8) bottom_hold();
  translate([0,0, 87.5]) color("fuchsia", 0.8) up_hold();  
  translate([0,0, 82.4]) color("orange", 0.5) lens_hold();  

  translate([0,0, 89.5]) mirror([0,0,1]) bl_hold();
  translate([0,0, 90.2]) bl_hold();
  
  translate([0,0, 85.5])
  {
    film();
    translate([0,0, 0.3]) film_frame(4); 
    translate([0,0, 0.9]) mirror([0,0,1]) film_frame_cup(4);   
  }
  
  translate([0,20,96]) rotate([0,0,90]) color("gray") phone();
  translate([0,0,102]) phone_holder();  
  
//  for (x = [-1, 1], y = [-1, 1])
//    translate([x * 90/2, y * 70/2, 100]) knob();  
 }
 
 
 module phone()
 {
   hull() for (x = [-1, 1], y = [-1, 1])
   {
     translate([x * 150/2, y * 67/2,  5-1.25]) scale([1,1,0.25]) sphere(d=10);    
     translate([x * 150/2, y * 67/2, -5+1.25]) scale([1,1,0.25]) sphere(d=10);    
   } 
 }

module stencil()
{
  H=1;
  X=50;
  Y=45;
  difference() 
  {
    cube([X+20, Y+20, H], center = true);        
    {
      for (x = [-1, 1], y = [-1, 1])
        translate([x * (X/2-1), y * (Y/2-1), 0])
          cylinder(h = 10, d = 4, center = true);
    } 
    
    cube([X, Y, 10], center = true);        
    

  }     
}

 
 
 module phone_holder()
{
  difference()
  {
    union()
    {
      hull() for (x = [-1, 1], y = [-1, 1])
        translate([x * 90/2, y * 70/2, 0])
          cylinder(h = 2, d = 10, center = true);   
      for (x = [-1, 1], y = [-1, 1])
        translate([x * 90/2, y * 70/2, -6])
          cylinder(h = 10, d = 10, center = true);   
        translate([41, 0, -4]) cube([4, 70, 6], center=true);           
        translate([-41, 0, -4]) cube([4, 70, 6], center=true);        
        
        translate([22, -62, -6]) cube([20, 4, 10], center=true);        
        translate([-22, -62, -6]) cube([20, 4, 10], center=true);           
        translate([0, -44, 0]) cube([64, 40, 2], center=true);          
        translate([0, -62, -2]) cube([64, 4, 2], center=true);        
        
    }
      translate([35, 0, 0]) hull()
      { 
        scale([0.7,1,1]) cylinder(h = 20, d=40, center = true);   
        translate([15, 0, 0]) cube([4, 40, 20], center=true);     
      }  
        
      translate([-35, 0, 0]) hull()
      { 
        scale([0.7,1,1]) cylinder(h = 20, d=40, center = true);   
        translate([-15, 0, 0]) cube([4, 40, 20], center=true);     
      } 
      
      translate([0, -35, 0]) cylinder(h = 20, d=36, center = true); 
      translate([0, 18, 0]) cylinder(h = 20, d=32, center = true); 
      
      for (x = [-1, 1], y = [-1, 1])
        translate([x * 90/2, y * 70/2, 0])
          cylinder(h = 30, d = 3.2, center = true);    
  }
} 

 module knob()
{  
  height=6;
  diameter=22;    
  chamfer=0.6;
    
  difference()      
  {
    union()
    { 
      translate([0,0,chamfer]) cylinder(d=diameter,h=height-2*chamfer);           
      translate([0,0,height-chamfer]) cylinder(d1=diameter,d2=diameter-chamfer*2, h=chamfer);      
      cylinder(d1=diameter-chamfer*2,d2=diameter, h=chamfer);          
    }      
           
    translate([0,0,-1]) cylinder(d=3.2,h=height+2);     
    translate([0,0,height-3]) cylinder(d=6.8,h=4, $fn=6);      
    
    //knurls
    for(i=[0:29], t=[120,-120]) rotate([0,0,i*12])
      linear_extrude(height=height+0.1, twist=height/45*t)
        translate([diameter/2,0]) circle(r=0.5, $fn=4);    
  }
}

 
module ring()
{
  difference()
  {
    cylinder(h=6.5, d=58.6, center=true);
    cylinder(h=10, d=54.4, center=true);  
  }

  intersection()
  {
    difference()
    {
      translate([0,0,-2.45]) cylinder(h=1.6, d=58.6, center=true);
      cylinder(h=10, d=52.2, center=true);  
    }

    for(i = [0:2]) 
    {      
      rotate([0, 0, i*120]) translate([0, 0, 0]) 
      {
        hull()
        {
          cylinder(h = 10, d = 0.1, center = true);
          translate([0, 56/2,0]) cube([24,0.2,10], center = true);
        }
      }
    } 
  }
  
  difference()
  {
    translate([0,0,-2.15]) cylinder(h=2.2, d=58.6+4, center=true);
    cylinder(h=10, d=54.4, center=true);  
  }  
}


module bolt()
{
  translate([0,0,11.75]) difference()
  {
    trapezoidal_threaded_rod(d = 62, pitch = 4, length = 30,thread_angle = 60, thread_depth=1.5);           
    cylinder(h=100, d=54.4, center=true);  
  } 
  ring();
}

module bottom_hold()
{
  difference() 
  {
    hull()
    {
      for (x = [-1, 1], y = [-1, 1])
        translate([x * 100/2, y * 80/2, 0])
          cylinder(h = 2, d = 4, center = true);
    }  
    cube([36.5, 24.5, 10], center = true);  
    translate([0,0, 0.6]) cube([120, 35+10+0.4, 0.85], center = true);     
    for (x = [-1, 1], y = [-1, 1])
      translate([x * 90/2, y * 70/2, 0])
          cylinder(h = 10, d = 3.2, center = true);      
  }
}

module bl()
{
  difference()
  {
    cube([59, 75, 0.21], center = true); 
  
    translate([15,-36, 0]) hull()
    {
      cylinder(h = 5, d = 6, center = true);  
      translate([0,-5, 0])  cylinder(h = 5, d = 6, center = true);  
    }
    translate([-15,-36, 0]) hull()
    {
      cylinder(h = 5, d = 6, center = true);  
      translate([0,-5, 0])  cylinder(h = 5, d = 6, center = true);  
    } 
  }
}

module bl_hold()
{
  H=0.6;
  difference() 
  {
    hull()
    {
      for (x = [-1, 1], y = [-1, 1])
        translate([x * 100/2, y * 80/2, 0])
          cylinder(h = H, d = 4, center = true);
    } 
    
     
    cube([36.5, 24.5, 20], center = true);      
 
    // holes for bolts
    for (x = [-1, 1], y = [-1, 1])
      translate([x * 90/2, y * 70/2, 0])
          cylinder(h = 10, d = 3.2, center = true);      
    translate([-50,0, 0]) hull()
    {  
      scale([0.5,1,1]) cylinder(h = 10, d = 45.4, center = true);
      translate([-30,0, 0]) cube([2, 45.4, 10], center = true);    
    }          
 
    translate([50,0, 0]) hull()
    {  
      scale([0.5,1,1]) cylinder(h = 10, d = 45.4, center = true);
      translate([30,0, 0]) cube([2, 45.4, 10], center = true);    
    }          


 
    
    translate([0,10, -0.2]) cube([60, 80, 0.21], center = true);      
    translate([0,43, 0])  scale([1, 0.5,1]) cylinder(h = 10, d = 60, center = true);
  }     

    translate([15,-28, 0]) hull()
    {
      cylinder(h = H, d = 5, center = true);  
      translate([0,-5, 0])  cylinder(h = H, d = 5, center = true);  
    }
    translate([-15,-28, 0]) hull()
    {
      cylinder(h = H, d = 5, center = true);  
      translate([0,-5, 0])  cylinder(h = H, d = 5, center = true);  
    }    
}


module up_hold()
{
  H=3;
  difference() 
  {
    hull()
    {
      for (x = [-1, 1], y = [-1, 1])
        translate([x * 100/2, y * 80/2, 0])
          cylinder(h = H, d = 4, center = true);
    } 
    
     
    cube([36.5, 24.5, 20], center = true);      
    translate([0,0, -H/2+0.44]) cube([120, 45.4, 0.9], center = true);  // film tray  
    // holes for bolts
    for (x = [-1, 1], y = [-1, 1])
      translate([x * 90/2, y * 70/2, 0])
          cylinder(h = 10, d = 3.2, center = true);      
    translate([-50,0, 0]) 
    {
      hull()
      {  
        scale([0.5,1,1]) cylinder(h = 10, d = 45.4, center = true);
        translate([-30,0, 0]) cube([2, 45.4, 10], center = true);    
      }          
      translate([0,0, -H/2]) hull()
      {
        scale([0.7,1,1]) cylinder(h = 0.2, d = 45.4, center = true);
        translate([0,0, 2]) scale([0.5,1,1]) cylinder(h = 0.1, d = 45.4, center = true);
      }
    }
  
    translate([50,0, 0])
    { 
      hull()
      {  
        scale([0.5,1,1]) cylinder(h = 10, d = 45.4, center = true);
        translate([30,0, 0]) cube([2, 45.4, 10], center = true);    
      }          

      translate([0,0, -H/2]) hull()
      {
        scale([0.7,1,1]) cylinder(h = 0.2, d = 45.4, center = true);
        translate([0,0, 2]) scale([0.5,1,1]) cylinder(h = 0.1, d = 45.4, center = true);
      }        
    }

  
    
  }     
}


module lens_hold()
{
    difference() 
    {
      hull()
      {
        for (x = [-1, 1], y = [-1, 1])
          translate([x * 100/2, y * 80/2, 0])
            cylinder(h = 3, d = 4, center = true);
      }  
      translate([0,0, 0.6]) cylinder(d=74.4, h=2, center=true); 
      translate([0,0, 0.6]) cylinder(d=68.4, h=10, center=true);       
      for (x = [-1, 1], y = [-1, 1])
        translate([x * 90/2, y * 70/2, 0])
            cylinder(h = 10, d = 3.2, center = true);      
  }
}

module nut()
{
//  H=48;
  H=36;  
  translate([0,0,-(H-2)/2]) difference()
  { 
    cylinder(d=74, h=2, center=true);
    cylinder(d=65, h=10, center=true);
  }

  difference()
  {
    cylinder(d=68, h=H, center=true);
    translate([0,0,H/2 +0.1]) 
    // Внутренняя трапецеидальная резьба
    trapezoidal_threaded_rod(d=62, pitch=4, length=H+1, thread_angle=60,
                             thread_depth=1.5, internal=true, $slop=0.2, anchor=UP);
  }
}


perfostep=18.999/4;
perfoY = 2.794;
perfoX = 1.981;
    
module film()
{
  color("black")
  difference()
  {
    cube([120,35,0.12], center = true);
    
    for(x = [-2:2]) translate([perfostep*8*x, 0 ,0]) cube([36, 24, 1], center = true);
    
    for(x = [-14:14])   
    {
      translate([perfostep*x+perfostep/2, 28.169/2,0]) cube([perfoX, perfoY, 1], center = true);  
      translate([perfostep*x+perfostep/2, -28.169/2,0]) cube([perfoX, perfoY, 1], center = true);
    }
  }
  color("blue", 0.2)  
  for(x = [-1:1]) translate([perfostep*8*x, 0 ,0]) cube([36, 24, 1], center = true);  
}

    
module film_frame(N=3)
{
  H=1.2;
  length = perfostep*8*N+2*perfostep;
  difference()
  {
    cube([ length+16, 35+10, H], center = true);
    cube([ length+2, 24, 10], center = true);
    translate([0,0,0.2]) cube([ length+8, 35+0.4, H], center = true);    
    
  }
  
  perfN = N*8 + 2;
    for(x = [-perfN/2:perfN/2-1])   
    {
      translate([perfostep*x+perfostep/2, 28.169/2,0]) perfo_tooth(H);  
      translate([perfostep*x+perfostep/2, -28.169/2,0]) perfo_tooth(H);      
    }

}

module film_frame_cup1(N=3)
{
  H=1.0;
  length = perfostep*8*N+2*perfostep;
  difference()
  {
    cube([ length+8-0.5, 35+0.4-0.3, H], center = true);    
    cube([ length+2+1, 24+0.1, 10], center = true);    
    perfN = N*8 + 2;
    for(x = [-perfN/2:perfN/2-1])   
    {
      translate([perfostep*x+perfostep/2, 28.169/2,0]) cube([perfoX+0.1, perfoY+0.1, 10] , center = true);  
      translate([perfostep*x+perfostep/2, -28.169/2,0]) cube([perfoX+0.1, perfoY+0.1, 10] , center = true);  
    }
  } 
}


module film_frame_cup(N = 3, group_size = 4)
{
  H = 1.2;
  length = perfostep * 8 * N + 2 * perfostep;
  perfN = N * 8 + 2;

  module perfo_hole(x) 
  {
    translate([x, 0, 0.11])
      cube([perfoX + 0.0, perfoY + 0.0, 1], center = true);
  }

  difference()
  {
    //cube([length + 8 - 0.5, 35 + 0.4 - 0.5, H], center = true);  // !!!
    hull()
    {
      for (x = [-1, 1], y = [-1, 1])
        translate([x*(length + 8 - 0.5-4)/2, y*(35 + 0.4 - 0.5-4)/2, 0])
          cylinder(h = H, r = 2, center = true);
    }      
    cube([length + 2 + 1, 24 + 0.1, 10], center = true);
    for (side = [-1, 1])
    {
      y = side * (28.169 / 2);      
      translate([0, y, 0])
      for (start = [0 : group_size : perfN - 1]) 
      {
        end = min(start + group_size, perfN);    
        hull() 
        {
          for (i = [start : end - 1]) 
          {
            x = perfostep * (i - (perfN - 1) / 2);
            perfo_hole(x);
          }
        }
      }
    }
  }
}

module perfo_tooth(H=1, gap=-0.15)
{
  hull()
  {
    for (x = [-1, 1], y = [-1, 1])
        translate([x * (perfoX/2-0.5+gap), y * (perfoY/2-0.5+gap), 0])
          cylinder(h = H, d = 1, center = true);
    } 
    

}

