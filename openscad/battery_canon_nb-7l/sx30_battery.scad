$fn=96;
//translate([-16.1, -22.6, -8.9]) color("Blue", alpha=1) import("dummy.stl");

//color("red", alpha=0.5)
box();
translate([0, 0, 7.25]) cup();

module cup()
{
  difference()
  {
    cube([30-0.4,42-0.4,3], center=true);
    
    translate([-6.8, -16.0, 0])
    {
      cylinder(h=20, d=3.3, center=true);       
      translate([0, 0, 1.5]) cylinder(h=4, d=6.8, center=true);
    }

    translate([11, 17.5, 0])
    {
      cylinder(h=20, d=3.3, center=true);       
      translate([0, 0, 1.5]) cylinder(h=4, d=6.8, center=true);
    }
  }

}

module box()
{
  difference()
  { 
    union()
    {
      difference()
      {
        cube([31.7,45,17.5], center=true);
        translate([0, 0, 8]) cube([30,42,5], center=true);
        translate([0, 1, 2.1]) cube([26,38,16], center=true);
      }
      translate([-6, -18, -1]) cube([14,4,13], center=true);
      translate([-6.8, -16.0, -5]) cylinder(h=6, d=10, center=true);
      translate([-6.8, -16.0, -1.5]) cylinder(h=14, d=6, center=true);    
      translate([11, 17.5, -5]) cylinder(h=6, d=10, center=true);
      translate([11, 17.5, -1.5]) cylinder(h=14, d=6, center=true);      
      translate([13, 19.5, -1.5]) cube([1,1,14], center=true);    
    }
    step=5.05-1.8;
    translate([-1.8, -22, -5.2]) cube([2,4,4], center=true);
    translate([-1.8-step, -22, -5.2]) cube([2,4,4], center=true);
    translate([-1.8-2*step, -22, -5.2]) cube([2,4,4], center=true);
    translate([-1.8-3*step, -22, -5.2]) cube([2,4,4], center=true);

    translate([-1.8, -20.0, 1.5]) cylinder(h=20, d=1.8, center=true);
    translate([-1.8, -17.0, 1.5]) cylinder(h=20, d=1.8, center=true);
    translate([-1.8, -18, 5]) cube([2, 5, 3], center=true);
    translate([-1.8, -15.9, 3]) cube([2, 2, 6], center=true);
  
    translate([-1.8-3*step, -20.0, 1.5]) cylinder(h=20, d=1.8, center=true);
    translate([-1.8-3*step, -17.0, 1.5]) cylinder(h=20, d=1.8, center=true);
    translate([-1.8-3*step, -18, 5]) cube([2, 5, 3], center=true);
    translate([-1.8-3*step, -15.9, 3]) cube([2, 2, 6], center=true);

    translate([-15.2, -22.3, -4.9]) cube([2,4,4], center=true);
    translate([14.7, -22.3, -4.9]) cube([2.5,4,4], center=true);
   
    translate([-6.8, -16.0, 0])
    {
      cylinder(h=20, d=3.3, center=true);    
      hull()
      {
        translate([0, 0, -7]) cylinder(h=6, d=6.8, center=true, $fn=6); 
        translate([0, 0, -6]) cylinder(h=6, d=3.3, center=true, $fn=6);  
      }
    }
  
    translate([11, 17.5, 0])
    {
      cylinder(h=20, d=3.3, center=true);    
      hull()
      {
        translate([0, 0, -7]) cylinder(h=6, d=6.8, center=true, $fn=6); 
        translate([0, 0, -6]) cylinder(h=6, d=3.3, center=true, $fn=6);  
      }
    }  
    translate([-13, 18.5, 4]) cube([14,3,12], center=true);
  }
}

      
